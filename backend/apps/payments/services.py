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
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from apps.audit import services as audit
from apps.common.exceptions import DomainConflict
from apps.packages.models import Package
from apps.students.models import Student
from apps.studios.models import Studio

from . import gateway, iban, selectors
from .models import CheckoutSession, Payment, PaymentInstructions, Receipt, WebhookEvent


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


def record_webhook_event(event: dict[str, Any]) -> tuple[WebhookEvent, bool]:
    """Salva un evento verificato una volta sola; in coda solo alla prima consegna."""
    from .tasks import process_webhook_event  # tasks importa services: evita un ciclo

    with transaction.atomic():
        stored, created = WebhookEvent.objects.get_or_create(
            stripe_event_id=event["id"],
            defaults={"type": event.get("type", ""), "payload": event},
        )
        if created:
            # Dopo il commit: il worker deve poter leggere la riga che deve elaborare.
            transaction.on_commit(lambda: process_webhook_event.delay(stored.pk))
    return stored, created


# Eventi che chiudono il pagamento come riuscito.
FULFIL_EVENTS = {"checkout.session.completed", "checkout.session.async_payment_succeeded"}
# Tutti gli eventi di cui ci occupiamo; gli altri si salvano e si ignorano.
HANDLED_EVENTS = FULFIL_EVENTS | {
    "checkout.session.async_payment_failed",
    "checkout.session.expired",
}


def process_webhook_event(event_pk: int) -> bool:
    """Applica un evento salvato esattamente una volta. Si può chiamare quante volte si vuole."""
    with transaction.atomic():
        # Blocco di riga: due worker sullo stesso evento si accodano invece di sovrapporsi.
        event = WebhookEvent.objects.select_for_update().get(pk=event_pk)
        if event.processed_at is not None:
            return False  # già elaborato: nessun effetto
        event.attempts += 1
        if event.type in HANDLED_EVENTS:
            session = gateway.SessionInfo.from_dict(event.payload["data"]["object"])
            _apply_to_checkout(session, failed=event.type.endswith("async_payment_failed"))
        event.processed_at = timezone.now()
        event.save(update_fields=["processed_at", "attempts"])
        return True


def _apply_to_checkout(session: gateway.SessionInfo, *, failed: bool = False) -> None:
    # Ritrova il tentativo dalla sessione di Stripe e ne aggiorna lo stato.
    checkout = (
        CheckoutSession.objects.select_for_update()
        .select_related("package__student")
        .filter(stripe_session_id=session.id)
        .first()
    )
    if checkout is None:
        # Non è un errore: può essere un evento di un altro ambiente o di un test.
        logger.warning("Stripe session %s matches no checkout attempt; ignored", session.id)
        return
    apply_session_state(checkout, session, failed=failed)


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
