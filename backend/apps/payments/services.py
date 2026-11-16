"""Scritture dei pagamenti: registrazione a mano e checkout online (Stripe).

Qui vive la logica; le view e i task sono involucri sottili
(docs/learning/concetti/service-layer-e-modular-monolith.md, ADR-002).
Per i pagamenti online leggere prima docs/learning/concetti/pagamenti-online-stripe.md,
ADR-013 (Stripe Checkout) e ADR-014 (webhook salvati, poi elaborati).

FUTURO (pagamenti dentro l'app): `start_checkout` è il punto da cui partirebbe un pagamento
reale. Prima di attivarlo servono le decisioni elencate in testa a models.py (ADR da scrivere,
prossimo numero libero: ADR-034).
"""

import datetime
import logging
import uuid
from collections.abc import Callable
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max, Sum
from django.utils import timezone

from apps.audit import services as audit
from apps.common.exceptions import DomainConflict, DomainError
from apps.packages.models import Package
from apps.students.models import Student
from apps.studios.models import Studio

from . import gateway, iban, selectors
from .models import (
    CheckoutSession,
    Payment,
    PaymentInstructions,
    Receipt,
    StudioPaymentAccount,
    WebhookEvent,
)


def ensure_package_matches_student(student: Student, package: Package | None) -> None:
    """L'unico punto che impone: il pacchetto di un pagamento appartiene al suo studente."""
    if package is not None and package.student_id != student.pk:
        raise ValidationError(
            {"package": "Package must belong to the same student as the payment."}
        )


def _author(actor: Any) -> Any:
    # Chi ha creato la riga: l'utente se c'è davvero, altrimenti nessuno (webhook, sistema).
    return actor if getattr(actor, "pk", None) else None


def _record_audit(payment: Payment, actor: Any) -> None:
    # Ogni pagamento registrato lascia una traccia nel registro attività (ADR-031).
    # Nei metadati metodo e importo; mai dati personali (docs/learning/concetti/audit-log.md).
    audit.record(
        audit.Action.PAYMENT_RECORD,
        actor=actor,
        target=payment,
        studio_id=payment.student.studio_id,
        metadata={"method": payment.method, "amount": str(payment.amount)},
    )


def create_payment(
    *, student: Student, package: Package | None = None, actor: Any = None, **fields: Any
) -> Payment:
    """Registra un pagamento a mano. `actor` è l'utente collegato (None se è il sistema)."""
    ensure_package_matches_student(student, package)
    payment = Payment.objects.create(
        student=student, package=package, recorded_by=_author(actor), **fields
    )
    _record_audit(payment, actor)
    return payment


# Le uniche variazioni di stato consentite. "paid" è definitivo: una registrazione di denaro
# non deve tornare indietro in silenzio.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    Payment.Status.PENDING: frozenset({Payment.Status.PAID, Payment.Status.OVERDUE}),
    Payment.Status.OVERDUE: frozenset({Payment.Status.PAID}),
    Payment.Status.PAID: frozenset(),
    # Lo storno non cambia mai stato (e update_payment lo rifiuta prima di arrivare qui).
    Payment.Status.REVERSAL: frozenset(),
}


def ensure_transition_allowed(current: str, target: str) -> None:
    """Solleva ValidationError se il cambio di stato non è nella tabella qui sopra."""
    if target != current and target not in ALLOWED_TRANSITIONS[current]:
        raise ValidationError({"status": f"Cannot change status from {current} to {target}."})


def ensure_not_final(payment: Payment) -> None:
    """Un pagamento pagato o uno storno è definitivo (fase 8, FR-001): niente modifica, niente
    cancellazione. Si corregge con `reverse_payment`. Pending e overdue restano modificabili."""
    if payment.status in (Payment.Status.PAID, Payment.Status.REVERSAL):
        raise PaymentFinal("This entry is final: reverse it instead of changing it.")


def update_payment(payment: Payment, **changes: Any) -> Payment:
    """Modifica un pagamento controllando transizione di stato e coerenza del pacchetto.

    Solo pending e overdue: un pagamento pagato non si tocca più (`ensure_not_final`).
    """
    ensure_not_final(payment)
    if "status" in changes:
        ensure_transition_allowed(payment.status, changes["status"])
    for field, value in changes.items():
        setattr(payment, field, value)
    ensure_package_matches_student(payment.student, payment.package)
    payment.save()
    return payment


def delete_payment(payment: Payment, *, actor: Any) -> None:
    """Cancella un pagamento in attesa o scaduto (non ancora incassato). Lascia una traccia.

    La voce di audit si scrive prima della cancellazione, con importo e metodo: dopo non ci
    sarebbe più nulla da descrivere. Un pagamento pagato non si cancella mai.
    """
    ensure_not_final(payment)
    audit.record(
        audit.Action.PAYMENT_DELETE,
        actor=actor,
        target=payment,
        studio_id=payment.student.studio_id,
        metadata={
            "method": payment.method,
            "amount": str(payment.amount),
            "status": payment.status,
        },
    )
    payment.delete()


def reverse_payment(payment: Payment, *, reason: str, actor: Any) -> Payment:
    """Storna un pagamento pagato: crea una riga di storno collegata, l'originale non si tocca.

    L'originale resta "paid" e visibile; lo storno porta chi, quando e perché ed è datato a
    oggi (mai a ritroso), così un mese già consegnato al commercialista non cambia. Una sola
    volta per pagamento: lo garantisce il vincolo di unicità sul collegamento, e il lock sulla
    riga dell'originale fa perdere con un 409 pulito chi arriva secondo. Non restituisce denaro:
    corregge il registro (FR-007). Spiegazione: docs/learning/concetti/registro-di-cassa.md.
    """
    reason = reason.strip()
    if not reason or len(reason) > 200:
        raise ValidationError({"reason": "A reason of 1 to 200 characters is required."})
    with transaction.atomic():
        original = Payment.objects.select_for_update().select_related("student").get(pk=payment.pk)
        if original.status == Payment.Status.REVERSAL:
            raise IsReversal("A reversal cannot be reversed.")
        if original.status != Payment.Status.PAID:
            raise NotPaid("Only a paid entry can be reversed.")
        if Payment.objects.filter(reversal_of=original).exists():
            raise AlreadyReversed("This entry was already reversed.")
        try:
            with transaction.atomic():
                reversal = Payment.objects.create(
                    student=original.student,
                    package=original.package,
                    amount=original.amount,
                    date=timezone.localdate(),
                    method=original.method,
                    status=Payment.Status.REVERSAL,
                    reversal_of=original,
                    reason=reason,
                    recorded_by=_author(actor),
                )
        except IntegrityError as exc:
            # Un'altra richiesta ha stornato lo stesso pagamento tra il controllo e l'insert.
            raise AlreadyReversed("This entry was already reversed.") from exc
        audit.record(
            audit.Action.PAYMENT_REVERSE,
            actor=actor,
            target=reversal,
            studio_id=original.student.studio_id,
            metadata={"method": original.method, "amount": str(original.amount)},
        )
    return reversal


class ProviderReversalResult:
    """Esito di `add_provider_reversal`: cosa è successo alla notifica del fornitore."""

    CREATED = "created"  # nuova riga di storno
    DUPLICATE = "duplicate"  # lo stesso rimborso o la stessa contestazione era già registrato
    EXCEEDS = "exceeds"  # la somma degli storni supererebbe l'importo: niente scritto
    NOT_APPLICABLE = "not_applicable"  # non è un pagamento incassato: niente scritto


def add_provider_reversal(
    original: Payment, *, amount: Decimal, cause: str, provider_ref: str
) -> tuple[Payment | None, str]:
    """Aggiunge uno storno dovuto a un rimborso o a una contestazione persa (fase 9, ADR-038).

    Come per lo storno manuale l'originale non si tocca mai: nasce una riga nuova, datata a oggi
    (un mese già consegnato al commercialista non cambia). A differenza dello storno manuale può
    essere parziale e un pagamento può averne più d'uno; la regola è che la somma degli storni non
    supera mai l'importo. Non si può esprimere come vincolo del database, quindi si controlla qui
    sotto il lock di riga dell'originale (lo stesso schema dei numeri di ricevuta); un secondo
    storno contemporaneo aspetta e poi vede la somma aggiornata. `provider_ref` (id Stripe) è unico:
    una notifica ripetuta non crea una seconda riga. Ritorna la riga creata (o None) e l'esito.
    """
    if cause not in (Payment.Cause.REFUND, Payment.Cause.DISPUTE) or amount <= 0:
        raise ValueError(
            "A provider reversal needs a refund or dispute cause and a positive amount."
        )
    with transaction.atomic():
        locked = Payment.objects.select_for_update().select_related("student").get(pk=original.pk)
        if locked.status != Payment.Status.PAID:
            return None, ProviderReversalResult.NOT_APPLICABLE
        if Payment.objects.filter(provider_ref=provider_ref).exists():
            return None, ProviderReversalResult.DUPLICATE
        already = Payment.objects.filter(reversal_of=locked).aggregate(total=Sum("amount"))["total"]
        if (already or Decimal("0.00")) + amount > locked.amount:
            return None, ProviderReversalResult.EXCEEDS
        try:
            with transaction.atomic():
                reversal = Payment.objects.create(
                    student=locked.student,
                    package=locked.package,
                    amount=amount,
                    date=timezone.localdate(),
                    method=locked.method,
                    status=Payment.Status.REVERSAL,
                    reversal_of=locked,
                    cause=cause,
                    provider_ref=provider_ref,
                )
        except IntegrityError:
            # Un'altra notifica con lo stesso id è passata tra il controllo e l'insert.
            return None, ProviderReversalResult.DUPLICATE
        audit.record(
            audit.Action.PAYMENT_REFUND
            if cause == Payment.Cause.REFUND
            else audit.Action.PAYMENT_DISPUTE,
            actor=None,  # lo fa il fornitore, non una persona
            target=reversal,
            studio_id=locked.student.studio_id,
            metadata={"cause": cause, "amount": str(amount), "ref": provider_ref},
        )
    return reversal, ProviderReversalResult.CREATED


# --- Pagamenti online (fase 3, ADR-013/014) ----------------------------------------------

logger = logging.getLogger(__name__)


class PaymentFinal(DomainConflict):
    """Un pagamento pagato (o uno storno) è definitivo: si corregge con uno storno."""

    code = "payment_final"


class NotPaid(DomainConflict):
    """Lo storno e la ricevuta esistono solo per un pagamento pagato."""

    code = "not_paid"


class AlreadyReversed(DomainConflict):
    """Un pagamento si storna al massimo una volta (anche con due richieste insieme)."""

    code = "already_reversed"


class IsReversal(DomainConflict):
    """Una riga di storno non si storna né riceve una ricevuta."""

    code = "is_reversal"


class PackageAlreadyPaid(DomainConflict):
    """Il pacchetto è già pagato: l'API risponde 409."""

    code = "package_already_paid"


def package_is_paid(package: Package) -> bool:
    """Vero se il pacchetto ha almeno un pagamento "paid" che non sia stato stornato."""
    return selectors.effective_paid(Payment.objects.filter(package=package)).exists()


def _cents(amount: Decimal) -> int:
    # Stripe vuole interi in centesimi: si lavora con Decimal, mai con float, per i soldi.
    return int((amount * 100).quantize(Decimal("1")))


def start_checkout(package: Package, *, user: Any) -> CheckoutSession:
    """Restituisce un tentativo di checkout aperto per `package`, creandolo se serve.

    La riga del pacchetto resta bloccata per tutta l'operazione, chiamata a Stripe compresa:
    un doppio clic aspetta la prima richiesta e poi riusa il suo tentativo, invece di aprire
    una seconda pagina di pagamento. La chiamata a Stripe porta una chiave di idempotenza,
    quindi nemmeno i nuovi tentativi di rete dell'SDK possono creare sessioni doppie. Se Stripe
    fallisce, la transazione torna indietro e nessun tentativo viene salvato.
    """
    if package_is_paid(package):
        raise PackageAlreadyPaid("This package is already paid.")
    with transaction.atomic():
        # Blocca e rilegge: il prezzo addebitato è quello nel database in questo momento.
        package = Package.objects.select_for_update().select_related("student").get(pk=package.pk)
        # Un tentativo ancora valido (aperto, con almeno un minuto davanti) si riusa.
        reusable = (
            CheckoutSession.objects.filter(
                package=package,
                status=CheckoutSession.Status.OPEN,
                stripe_session_id__isnull=False,
                expires_at__gt=timezone.now() + datetime.timedelta(minutes=1),
            )
            .order_by("-created_at")
            .first()
        )
        if reusable is not None:
            return reusable

        checkout = CheckoutSession.objects.create(
            package=package,
            created_by=user if getattr(user, "is_authenticated", False) else None,
            amount=package.price,
            currency=settings.STRIPE_CURRENCY,
        )
        info = gateway.create_checkout_session(
            checkout_id=str(checkout.id),
            amount_cents=_cents(package.price),
            currency=checkout.currency,
            description=f"{package.total_lessons} lessons — {package.student.full_name}",
            expires_at=timezone.now() + datetime.timedelta(minutes=settings.CHECKOUT_TTL_MINUTES),
            idempotency_key=f"checkout-{checkout.id}",
            customer_email=getattr(user, "email", None)
            if getattr(user, "role", "") == "parent"
            else None,
        )
        checkout.stripe_session_id = info.id
        checkout.url = info.url
        checkout.expires_at = info.expires_at
        checkout.save(update_fields=["stripe_session_id", "url", "expires_at", "updated_at"])
        return checkout


# Cosa si conserva di un evento (ADR-039): identificativi, stati e importi. Niente nomi, email,
# indirizzi o dati di carta: una copia grezza dell'evento sarebbe una copia di dati personali che
# nessuno potrebbe esportare né cancellare (constitution X).
_EVENT_KEYS = ("id", "object", "type", "livemode", "account", "created")
_OBJECT_KEYS = (
    "id",
    "object",
    "status",
    "payment_status",
    "amount",
    "amount_total",
    "amount_refunded",
    "currency",
    "payment_intent",
    "charge",
    "client_reference_id",
    "expires_at",
    "reason",
)
_REFERENCE_KEYS = ("payment_intent", "charge")  # a volte arrivano espansi: si tiene solo l'id
_METADATA_KEYS = ("checkout_id", "studio_id")


def scrub_event(event: dict[str, Any]) -> dict[str, Any]:
    """Una copia dell'evento con i soli campi che servono a elaborarlo (lista bianca)."""
    obj = (event.get("data") or {}).get("object") or {}
    kept: dict[str, Any] = {k: obj[k] for k in _OBJECT_KEYS if k in obj}
    for key in _REFERENCE_KEYS:
        if isinstance(kept.get(key), dict):
            kept[key] = kept[key].get("id")
    kept["metadata"] = {k: v for k, v in (obj.get("metadata") or {}).items() if k in _METADATA_KEYS}
    top = {k: event[k] for k in _EVENT_KEYS if k in event}
    return {**top, "data": {"object": kept}}


def record_webhook_event(event: dict[str, Any]) -> tuple[WebhookEvent, bool]:
    """Salva un evento verificato (ripulito) una volta sola; in coda solo alla prima consegna."""
    from .tasks import process_webhook_event  # tasks importa services: evita un ciclo

    with transaction.atomic():
        stored, created = WebhookEvent.objects.get_or_create(
            stripe_event_id=event["id"],
            defaults={
                "type": event.get("type", ""),
                "payload": scrub_event(event),
                # Il conto collegato che ha generato l'evento: così lo si attribuisce a uno studio.
                "stripe_account_id": event.get("account") or "",
                "livemode": bool(event.get("livemode")),
            },
        )
        if created:
            # Dopo il commit: il worker deve poter leggere la riga che deve elaborare.
            transaction.on_commit(lambda: process_webhook_event.delay(stored.pk))
    return stored, created


# Un gestore riceve l'evento (già bloccato, dentro la transazione) e ritorna l'esito.
EventHandler = Callable[[WebhookEvent], str]
EVENT_HANDLERS: dict[str, EventHandler] = {}


def handles(*event_types: str) -> Callable[[EventHandler], EventHandler]:
    """Registra un gestore per uno o più tipi di evento (ogni storia ne aggiunge)."""

    def register(handler: EventHandler) -> EventHandler:
        for event_type in event_types:
            EVENT_HANDLERS[event_type] = handler
        return handler

    return register


# Eventi che chiudono il pagamento come riuscito.
FULFIL_EVENTS = {"checkout.session.completed", "checkout.session.async_payment_succeeded"}
# Eventi di Checkout di cui ci occupiamo; gli altri si salvano e si ignorano.
HANDLED_EVENTS = FULFIL_EVENTS | {
    "checkout.session.async_payment_failed",
    "checkout.session.expired",
}


def _dispatch(event: WebhookEvent) -> str:
    # Si lavora solo in modalità test (constitution IV): un evento "live" si conserva e si ignora.
    if event.livemode:
        return WebhookEvent.Outcome.IGNORED
    # Un evento di un conto che nessuno studio ha collegato non si attribuisce a nessuno.
    if (
        event.stripe_account_id
        and not StudioPaymentAccount.objects.filter(
            stripe_account_id=event.stripe_account_id
        ).exists()
    ):
        return WebhookEvent.Outcome.IGNORED
    handler = EVENT_HANDLERS.get(event.type)
    return handler(event) if handler else WebhookEvent.Outcome.IGNORED


def process_webhook_event(event_pk: int) -> bool:
    """Applica un evento salvato esattamente una volta. Si può chiamare quante volte si vuole."""
    with transaction.atomic():
        # Blocco di riga: due worker sullo stesso evento si accodano invece di sovrapporsi.
        event = WebhookEvent.objects.select_for_update().get(pk=event_pk)
        if event.processed_at is not None:
            return False  # già elaborato: nessun effetto
        event.attempts += 1
        event.outcome = _dispatch(event)
        event.processed_at = timezone.now()
        event.save(update_fields=["processed_at", "attempts", "outcome", "attention_kind"])
        return True


@handles(*HANDLED_EVENTS)
def _handle_checkout_event(event: WebhookEvent) -> str:
    session = gateway.SessionInfo.from_dict(event.payload["data"]["object"])
    matched = _apply_to_checkout(session, failed=event.type.endswith("async_payment_failed"))
    return WebhookEvent.Outcome.APPLIED if matched else WebhookEvent.Outcome.IGNORED


def _apply_to_checkout(session: gateway.SessionInfo, *, failed: bool = False) -> bool:
    # Ritrova il tentativo dalla sessione di Stripe e ne aggiorna lo stato. Falso se non c'è.
    checkout = (
        CheckoutSession.objects.select_for_update()
        .select_related("package__student")
        .filter(stripe_session_id=session.id)
        .first()
    )
    if checkout is None:
        # Non è un errore: può essere un evento di un altro ambiente o di un test.
        logger.warning("Stripe session %s matches no checkout attempt; ignored", session.id)
        return False
    apply_session_state(checkout, session, failed=failed)
    return True


def apply_session_state(
    checkout: CheckoutSession, session: gateway.SessionInfo, *, failed: bool = False
) -> None:
    """Porta un tentativo (già bloccato) allo stato che Stripe riporta. Idempotente.

    Si completa solo quando i soldi ci sono: con metodi di pagamento differiti (per esempio
    l'addebito SEPA) la sessione si chiude come `unpaid` e l'esito arriva più tardi.
    """
    if checkout.status != CheckoutSession.Status.OPEN:
        return  # gli stati finali non cambiano più; le ripetizioni non fanno nulla
    if session.status == "complete" and session.payment_status in ("paid", "no_payment_required"):
        _fulfil(checkout, session)
    elif failed:
        checkout.status = CheckoutSession.Status.FAILED
        checkout.save(update_fields=["status", "updated_at"])
    elif session.status == "expired":
        checkout.status = CheckoutSession.Status.EXPIRED
        checkout.save(update_fields=["status", "updated_at"])


def _fulfil(checkout: CheckoutSession, session: gateway.SessionInfo) -> None:
    # Crea il pagamento "paid" e chiude il tentativo; il tutto dentro la transazione del chiamante.
    package = checkout.package
    if package_is_paid(package):
        # Pagato a mano nel frattempo: i soldi sono stati comunque presi, quindi si registra
        # e si avvisa nel log (rimborso da gestire a mano).
        logger.warning("Package %s was already paid; recording online payment too", package.pk)
    amount = (
        Decimal(session.amount_total) / 100 if session.amount_total is not None else checkout.amount
    )
    payment = Payment.objects.create(
        student=package.student,
        package=package,
        amount=amount,  # quanto Stripe ha davvero addebitato, anche se il prezzo è cambiato
        date=timezone.localdate(),
        method=Payment.Method.CARD,
        status=Payment.Status.PAID,
        checkout=checkout,
    )
    _record_audit(payment, None)
    checkout.status = CheckoutSession.Status.COMPLETED
    checkout.save(update_fields=["status", "updated_at"])


def reconcile_open_checkouts(limit: int = 100) -> int:
    """Rete di sicurezza per i webhook persi: chiede a Stripe dei tentativi aperti e scaduti."""
    stale = CheckoutSession.objects.filter(
        status=CheckoutSession.Status.OPEN,
        stripe_session_id__isnull=False,
        expires_at__lt=timezone.now(),
    ).values_list("pk", "stripe_session_id")[:limit]
    resolved = 0
    for pk, session_id in stale:
        if session_id is None:  # escluso dal filtro; serve solo a mypy
            continue
        session = gateway.retrieve_checkout_session(session_id)
        with transaction.atomic():
            checkout = (
                CheckoutSession.objects.select_for_update()
                .select_related("package__student")
                .get(pk=pk)
            )
            apply_session_state(checkout, session)
            resolved += checkout.status != CheckoutSession.Status.OPEN
    return resolved


# --- Istruzioni di pagamento dello studio (fase 8, ADR-036) -------------------------------

MAX_LINKS = 5
INSTRUCTION_FIELDS = ("account_holder", "iban", "bank_name", "note", "links")


def _clean_links(raw: Any) -> list[dict[str, str]]:
    """Fino a 5 link di pagamento esterni: etichetta di 1-40 caratteri e indirizzo `https`."""
    links = list(raw or [])
    if len(links) > MAX_LINKS:
        raise ValidationError({"links": f"At most {MAX_LINKS} payment links are allowed."})
    cleaned = []
    for item in links:
        label = str(item.get("label", "")).strip()
        url = str(item.get("url", "")).strip()
        parts = urlsplit(url)
        if not 1 <= len(label) <= 40:
            raise ValidationError({"links": "Each link needs a label of 1 to 40 characters."})
        # Solo https: un link `http`, `javascript:` o `data:` non deve mai arrivare a un genitore.
        if parts.scheme != "https" or not parts.netloc or len(url) > 500 or " " in url:
            raise ValidationError({"links": "Each link must be a secure https address."})
        cleaned.append({"label": label, "url": url})
    return cleaned


def _clean_instructions(data: dict[str, Any]) -> dict[str, Any]:
    holder = str(data.get("account_holder", "")).strip()
    raw_iban = str(data.get("iban", "")).strip()
    cleaned_iban = iban.normalise(raw_iban)
    if cleaned_iban and not iban.is_valid(cleaned_iban):
        raise ValidationError({"iban": "This IBAN is not valid. Check it and try again."})
    if cleaned_iban and not holder:
        raise ValidationError({"account_holder": "The account holder is required with an IBAN."})
    return {
        "account_holder": holder,
        "iban": cleaned_iban,
        "bank_name": str(data.get("bank_name", "")).strip(),
        "note": str(data.get("note", "")).strip(),
        "links": _clean_links(data.get("links")),
    }


def has_content(instructions: PaymentInstructions) -> bool:
    return any(getattr(instructions, field) for field in INSTRUCTION_FIELDS)


@transaction.atomic
def save_instructions(
    studio: Studio, *, actor: Any, data: dict[str, Any]
) -> PaymentInstructions | None:
    """Salva (o svuota) le istruzioni dello studio. Restituisce None se ora non ce ne sono.

    Un corpo tutto vuoto le cancella: nessuna riga con dati vuoti. Il registro delle azioni
    riceve solo i NOMI dei campi cambiati, mai i loro valori: l'IBAN non deve finire altrove
    (FR-023, SC-008). Non cambiando nulla non si scrive nulla.
    """
    new = _clean_instructions(data)
    current = PaymentInstructions.objects.select_for_update().filter(studio=studio).first()
    old = {f: getattr(current, f) for f in INSTRUCTION_FIELDS} if current else {}
    changed = [f for f in INSTRUCTION_FIELDS if new[f] != old.get(f, [] if f == "links" else "")]
    if not changed:
        return current if current and has_content(current) else None
    empty = not any(new.values())
    if empty:
        if current:
            current.delete()
        result = None
    else:
        result, _ = PaymentInstructions.objects.update_or_create(
            studio=studio, defaults={**new, "updated_by": _author(actor)}
        )
    audit.record(
        audit.Action.INSTRUCTIONS_CHANGE,
        actor=actor,
        target=result or current,
        studio_id=studio.pk,
        metadata={"fields": ",".join(changed), "cleared": empty},
    )
    return result


# --- Ricevute non fiscali (fase 8, ADR-035) ------------------------------------------------


def issue_receipt(payment: Payment, *, language: str, actor: Any) -> tuple[Receipt, bool]:
    """Emette la ricevuta di un pagamento incassato. Restituisce (ricevuta, creata ora?).

    Idempotente: se la ricevuta esiste già si restituisce quella, con lo stesso numero e la
    stessa lingua. Altrimenti si blocca la riga dello studio (`select_for_update`, come
    `add_teacher_to_studio`) e si prende `massimo + 1` per l'anno locale in corso: le emissioni
    contemporanee dello stesso studio si mettono in coda, quindi i numeri sono distinti e senza
    buchi; se la transazione annulla, il numero non è consumato. Si usa il massimo e non il
    conteggio perché i numeri restino unici anche se le ricevute vecchie spariscono con la
    conservazione. Il vincolo di unicità è la rete di sicurezza dietro il lock.
    Solo un pagamento "paid" ha una ricevuta: non una riga di storno, non uno in sospeso.
    """
    if language not in Receipt.Language.values:
        raise ValidationError({"language": "Choose it or en."})
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("student").get(pk=payment.pk)
        if payment.status == Payment.Status.REVERSAL:
            raise IsReversal("A reversal entry has no receipt.")
        if payment.status != Payment.Status.PAID:
            raise NotPaid("Only a paid entry has a receipt.")
        existing = Receipt.objects.filter(payment=payment).first()
        if existing is not None:
            return existing, False
        studio = Studio.objects.select_for_update().get(pk=payment.student.studio_id)
        year = timezone.localdate().year
        last = Receipt.objects.filter(studio=studio, year=year).aggregate(last=Max("sequence"))
        receipt = Receipt.objects.create(
            payment=payment,
            studio=studio,
            year=year,
            sequence=(last["last"] or 0) + 1,
            language=language,
            issued_by=_author(actor),
        )
        audit.record(
            audit.Action.RECEIPT_ISSUE,
            actor=actor,
            target=receipt,
            studio_id=studio.pk,
            metadata={"number": receipt.number},
        )
    return receipt, True


# --- Conto di pagamento dello studio (fase 9, ADR-037) -------------------------------------


class OnlinePaymentsOff(DomainError):
    """L'interruttore dei pagamenti online è spento: per chi chiama la funzione non esiste (404)."""

    status_code = 404
    code = "online_payments_off"


class NoPaymentAccount(DomainError):
    """Lo studio non ha ancora un conto di pagamento (404)."""

    status_code = 404
    code = "no_payment_account"


class AccountDisconnected(DomainConflict):
    """Il conto è stato scollegato da Stripe: per ripartire serve prima `restart_account`."""

    code = "account_disconnected"


class NotDisconnected(DomainConflict):
    """`restart_account` vale solo per un conto scollegato."""

    code = "not_disconnected"


class OnlinePaymentsNotAvailable(DomainConflict):
    """Lo studio non ha un conto attivo (o la funzione è spenta): non si può pagare online."""

    code = "online_payments_not_available"


def online_payments_enabled() -> bool:
    return bool(settings.ONLINE_PAYMENTS_ENABLED)


def require_online_payments() -> None:
    """Chiamata da ogni rotta del conto: con l'interruttore spento la funzione "non esiste"."""
    if not online_payments_enabled():
        raise OnlinePaymentsOff("Online payments are not available.")


def state_from_account(info: gateway.AccountInfo) -> str:
    """Lo stato dello studio, ricavato da ciò che Stripe riferisce (mai da ciò che supponiamo).

    Solo "attivo" permette di incassare. Un conto con requisiti aperti è "servono informazioni"
    (un conto appena creato lo è: Stripe aspetta i dati del titolare); "limitato" è un conto che
    Stripe ha bloccato senza chiedere altro; "in corso" è la verifica ancora in revisione.
    """
    state = StudioPaymentAccount.State
    if info.closed:
        return state.DISCONNECTED
    if info.card_payments == "active":
        return state.ACTIVE
    if info.card_payments == "pending":
        return state.IN_PROGRESS
    if info.open_requirements > 0:
        return state.INFORMATION_NEEDED
    if info.card_payments == "restricted":
        return state.RESTRICTED
    return state.IN_PROGRESS


def _portal_url(path: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}"


def _set_state(account: StudioPaymentAccount, new_state: str) -> bool:
    """Aggiorna lo stato se è cambiato e lo registra (l'autore è il fornitore, non una persona)."""
    if account.state == new_state:
        return False
    previous = account.state
    account.state = new_state
    account.state_changed_at = timezone.now()
    account.save(update_fields=["state", "state_changed_at", "updated_at"])
    audit.record(
        audit.Action.PAYMENT_ACCOUNT_STATE,
        actor=None,
        target=account,
        studio_id=account.studio_id,
        metadata={"from": previous, "to": new_state},
    )
    return True


def start_onboarding(studio: Studio, *, actor: Any) -> gateway.AccountLink:
    """Crea (una volta sola) il conto dello studio e ritorna dove mandare il titolare.

    La riga dello studio resta bloccata per tutta l'operazione, chiamata a Stripe compresa: un
    doppio clic aspetta il primo e poi vede il conto già creato, quindi ne esiste uno solo. Se
    Stripe non risponde la transazione torna indietro e non resta nulla. Non mandiamo a Stripe né
    email né nome: il titolare li scrive sulla pagina di Stripe (constitution X).
    """
    require_online_payments()
    with transaction.atomic():
        locked = Studio.objects.select_for_update().get(pk=studio.pk)
        account = StudioPaymentAccount.objects.filter(studio=locked).first()
        if account is not None and account.state == StudioPaymentAccount.State.DISCONNECTED:
            raise AccountDisconnected("The account was disconnected; start again first.")
        if account is None:
            info = gateway.create_account(
                studio_id=locked.pk, idempotency_key=f"account-studio-{locked.pk}-{uuid.uuid4()}"
            )
            account = StudioPaymentAccount.objects.create(
                studio=locked,
                stripe_account_id=info.id,
                state=state_from_account(info),
                created_by=actor if getattr(actor, "pk", None) else None,
            )
            audit.record(
                audit.Action.PAYMENT_ACCOUNT_START,
                actor=actor,
                target=account,
                studio_id=locked.pk,
                metadata={"state": account.state},
            )
        return gateway.create_account_link(
            account_id=account.stripe_account_id,
            return_url=_portal_url("/payment-instructions?return=1"),
            refresh_url=_portal_url("/payment-instructions?refresh=1"),
        )


def refresh_account(studio: Studio) -> StudioPaymentAccount:
    """Rilegge il conto da Stripe e aggiorna lo stato (alla fine dell'onboarding e a richiesta)."""
    require_online_payments()
    with transaction.atomic():
        account = StudioPaymentAccount.objects.select_for_update().filter(studio=studio).first()
        if account is None:
            raise NoPaymentAccount("This studio has no payment account yet.")
        info = gateway.retrieve_account(account.stripe_account_id)
        _set_state(account, state_from_account(info))
        return account


def restart_account(studio: Studio, *, actor: Any) -> None:
    """Toglie il collegamento morto di un conto scollegato, così si può ricominciare."""
    require_online_payments()
    with transaction.atomic():
        account = StudioPaymentAccount.objects.select_for_update().filter(studio=studio).first()
        if account is None:
            raise NoPaymentAccount("This studio has no payment account yet.")
        if account.state != StudioPaymentAccount.State.DISCONNECTED:
            raise NotDisconnected("Only a disconnected account can be started again.")
        audit.record(
            audit.Action.PAYMENT_ACCOUNT_STATE,
            actor=actor,
            target=account,
            studio_id=studio.pk,
            metadata={"from": account.state, "to": "removed"},
        )
        account.delete()


def refresh_accounts(limit: int = 200) -> int:
    """Rete di sicurezza oraria: rilegge i conti non scollegati e ritorna quanti sono cambiati.

    L'API v2 non ci manda eventi sullo stato del conto (spike, research R1): senza questo giro un
    conto bloccato da Stripe resterebbe "attivo" da noi, e un genitore proverebbe a pagare per
    nulla. Un errore su un conto non ferma gli altri.
    """
    if not online_payments_enabled():
        return 0
    changed = 0
    for account_id in (
        StudioPaymentAccount.objects.exclude(state=StudioPaymentAccount.State.DISCONNECTED)
        .order_by("id")
        .values_list("pk", flat=True)[:limit]
    ):
        try:
            with transaction.atomic():
                account = StudioPaymentAccount.objects.select_for_update().get(pk=account_id)
                info = gateway.retrieve_account(account.stripe_account_id)
                changed += _set_state(account, state_from_account(info))
        except (gateway.PaymentsUnavailable, StudioPaymentAccount.DoesNotExist):
            logger.warning("Could not refresh payment account #%s", account_id)
    return changed


@handles("account.application.deauthorized")
def _handle_account_deauthorized(event: WebhookEvent) -> str:
    # Lo studio ha scollegato MusicStudio dal suo Stripe: da qui in poi niente più pagamenti.
    account = (
        StudioPaymentAccount.objects.select_for_update()
        .filter(stripe_account_id=event.stripe_account_id)
        .first()
    )
    if account is None:
        return WebhookEvent.Outcome.IGNORED
    _set_state(account, StudioPaymentAccount.State.DISCONNECTED)
    return WebhookEvent.Outcome.APPLIED
