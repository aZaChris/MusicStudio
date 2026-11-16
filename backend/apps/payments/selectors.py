"""Letture dei pagamenti (solo query, nessuna scrittura).

Regola del progetto: le scritture stanno in services.py, le letture qui
(docs/learning/concetti/service-layer-e-modular-monolith.md, ADR-002).
"""

import calendar
import datetime
from decimal import Decimal
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import (
    Count,
    DecimalField,
    Exists,
    F,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.common.exceptions import PeriodTooLong
from apps.common.scoping import RECEIPT_PATHS, STUDENT_CHILD_PATHS, packages_visible_to, scope
from apps.common.tenancy import TenantContext
from apps.packages.models import Package

from .models import Payment, PaymentInstructions, Receipt, StudioPaymentAccount, WebhookEvent


def payments_for(ctx: TenantContext) -> QuerySet[Payment]:
    """I pagamenti che l'utente può vedere, e solo quelli.

    Il filtro per studio/insegnante passa SEMPRE da `scope`: è l'unico punto che isola i
    tenant (docs/learning/concetti/isolamento-tenant-e-bola.md, ADR-010). Il pagamento non ha
    un proprio studio: eredita quello dello studente, da qui STUDENT_CHILD_PATHS.
    `select_related("student")` evita una query per riga (concetti/orm-e-problema-n-piu-1.md).
    """
    # `receipt` è nel select_related, e lo storno è un'annotazione (`with_reversals`): così
    # `reversed`, `reversal_id` e `receipt_number` del serializer non costano una query per riga.
    return with_reversals(
        scope(Payment.objects.select_related("student", "receipt"), ctx, STUDENT_CHILD_PATHS)
    )


_MONEY = DecimalField(max_digits=12, decimal_places=2)


def _reversed_total(outer_key: str) -> Coalesce:
    # Somma degli importi delle righe di storno del pagamento `outer_key` (zero se non ce ne sono).
    total = (
        Payment.objects.filter(reversal_of=OuterRef(outer_key))
        .order_by()
        .values("reversal_of")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    return Coalesce(Subquery(total), Value(Decimal("0.00")), output_field=_MONEY)


def with_reversals(qs: QuerySet[Payment]) -> QuerySet[Payment]:
    """Aggiunge `reversed_amount` (somma degli storni del pagamento) e `first_reversal_id`.

    Dalla fase 9 un pagamento può avere più righe di storno (rimborsi parziali, ADR-038): lo
    "stornato" non è più un sì/no ma una somma. Sono sottoquery correlate, quindi entrano come
    colonne della stessa query, senza una query per riga e senza raggruppare il resto.
    """
    first = Payment.objects.filter(reversal_of=OuterRef("pk")).order_by("id").values("id")[:1]
    return qs.annotate(reversed_amount=_reversed_total("pk"), first_reversal_id=Subquery(first))


def not_fully_reversed() -> Q:
    """Filtro: il pagamento NON è stato stornato per intero (richiede `with_reversals`).

    Un rimborso parziale lascia il pagamento "incassato" (le lezioni ci sono state); lo storno
    intero, manuale o di un rimborso totale, no. Un importo a zero non risulta mai stornato.
    """
    return Q(reversed_amount=0) | Q(reversed_amount__lt=F("amount"))


def is_fully_reversed(amount: Decimal, reversed_amount: Decimal) -> bool:
    """Lo stesso criterio di `not_fully_reversed`, per un oggetto già in memoria."""
    return reversed_amount > 0 and reversed_amount >= amount


def effective_paid(qs: QuerySet[Payment]) -> QuerySet[Payment]:
    """I pagamenti che contano come denaro incassato: "paid" e non stornati per intero.

    Un pagamento stornato resta "paid" nel database (non si riscrive mai), ma non rende più
    pagato il pacchetto. Questa è l'unica definizione: checkout, stato dello studente e
    pacchetti aperti la usano tutti (specs/008-cash-register-receipts/research.md, R5). Dalla
    fase 9 conta lo storno per intero, non uno storno qualsiasi (specs/009, research R6).
    """
    return with_reversals(qs.filter(status=Payment.Status.PAID)).filter(not_fully_reversed())


def open_packages(ctx: TenantContext) -> QuerySet[Package]:
    """I pacchetti visibili a chi chiama che non hanno ancora un pagamento incassato."""
    paid = effective_paid(Payment.objects.filter(package=OuterRef("pk")))
    return packages_visible_to(ctx).filter(~Exists(paid))


# --- Registro di cassa: periodo, totali, righe (fase 8) ------------------------------------

ZERO = Decimal("0.00")
# Tutti i metodi compaiono sempre nei totali, anche a zero: la schermata ha sempre le stesse righe.
METHODS = [method for method, _ in Payment.Method.choices]


def current_month() -> tuple[datetime.date, datetime.date]:
    """Primo e ultimo giorno del mese corrente, in data locale (Europe/Rome)."""
    today = timezone.localdate()
    last = calendar.monthrange(today.year, today.month)[1]
    return today.replace(day=1), today.replace(day=last)


def ensure_period(
    date_from: datetime.date, date_to: datetime.date, *, max_days: int | None = None
) -> None:
    """Il periodo è coerente (da <= a) e, per le esportazioni, non supera `max_days` giorni."""
    if date_from > date_to:
        raise ValidationError({"date_to": "The end of the period is before its start."})
    if max_days is not None and (date_to - date_from).days + 1 > max_days:
        raise PeriodTooLong(f"The period cannot be longer than {max_days} days.")


def _payments_in_period(
    ctx: TenantContext, date_from: datetime.date, date_to: datetime.date
) -> QuerySet[Payment]:
    return payments_for(ctx).filter(date__gte=date_from, date__lte=date_to)


def register_summary(
    ctx: TenantContext, date_from: datetime.date, date_to: datetime.date
) -> dict[str, Any]:
    """Totali del registro per un periodo: incassato, stornato e netto, in totale e per metodo.

    Una sola query con somme condizionali, raggruppata per metodo (specs/008, research R4):
    incassato = pagamenti "paid" per la loro data; stornato = righe di storno per la loro
    data (più tarda); netto = incassato - stornato. In sospeso e scaduti si contano ma non si
    sommano mai. Un pagamento di novembre stornato il 3 dicembre resta in novembre e il suo
    storno cade in dicembre: un mese chiuso non cambia.
    """
    rows = (
        _payments_in_period(ctx, date_from, date_to)
        .order_by()
        .values("method")
        .annotate(
            received=Sum("amount", filter=Q(status=Payment.Status.PAID)),
            reversed=Sum("amount", filter=Q(status=Payment.Status.REVERSAL)),
            n_paid=Count("id", filter=Q(status=Payment.Status.PAID)),
            n_pending=Count("id", filter=Q(status=Payment.Status.PENDING)),
            n_overdue=Count("id", filter=Q(status=Payment.Status.OVERDUE)),
            n_reversal=Count("id", filter=Q(status=Payment.Status.REVERSAL)),
        )
    )
    by_method: dict[str, dict[str, Decimal]] = {
        m: {"received": ZERO, "reversed": ZERO} for m in METHODS
    }
    counts = {"paid": 0, "pending": 0, "overdue": 0, "reversal": 0}
    for row in rows:
        by_method[row["method"]] = {
            "received": row["received"] or ZERO,
            "reversed": row["reversed"] or ZERO,
        }
        counts["paid"] += row["n_paid"]
        counts["pending"] += row["n_pending"]
        counts["overdue"] += row["n_overdue"]
        counts["reversal"] += row["n_reversal"]
    lines: list[dict[str, Any]] = [
        {"method": m, **v, "net": v["received"] - v["reversed"]} for m, v in by_method.items()
    ]
    received = sum((v["received"] for v in by_method.values()), ZERO)
    reversed_ = sum((v["reversed"] for v in by_method.values()), ZERO)
    return {
        "period": {"from": date_from, "to": date_to},
        "totals": {"received": received, "reversed": reversed_, "net": received - reversed_},
        "by_method": lines,
        "counts": counts,
    }


def reversed_amount_of(payment: Payment) -> Decimal:
    """Somma degli storni di un pagamento: dall'annotazione se c'è, altrimenti con una query.

    Il percorso con la query serve solo per gli oggetti singoli (per esempio appena creati); gli
    elenchi passano sempre da `with_reversals` e non fanno query per riga.
    """
    annotated = getattr(payment, "reversed_amount", None)
    if annotated is not None:
        return Decimal(annotated)
    total = Payment.objects.filter(reversal_of=payment.pk).aggregate(total=Sum("amount"))["total"]
    return Decimal(total or ZERO)


def is_reversed(payment: Payment) -> bool:
    """Il pagamento è stato stornato per intero?"""
    return is_fully_reversed(payment.amount, reversed_amount_of(payment))


def _receipt_number(payment: Payment) -> str:
    try:
        return payment.receipt.number
    except ObjectDoesNotExist:
        return ""


def register_rows(
    ctx: TenantContext, date_from: datetime.date, date_to: datetime.date
) -> list[dict[str, Any]]:
    """Le righe del registro per l'esportazione: una per pagamento, in ordine di data.

    Importo con segno (negativo per lo storno) e stato "visibile": un originale stornato si
    legge `reversed`. Il numero di ricevuta c'è se la ricevuta è stata emessa.
    """
    rows = []
    for payment in _payments_in_period(ctx, date_from, date_to).order_by("date", "id"):
        is_reversal = payment.status == Payment.Status.REVERSAL
        reversed_ = is_reversed(payment)
        rows.append(
            {
                "date": payment.date,
                "receipt_number": _receipt_number(payment),
                "student": payment.student.full_name,
                "method": payment.method,
                "amount": -payment.amount if is_reversal else payment.amount,
                "status": "reversed" if reversed_ else payment.status,
                "reason": payment.reason,
                "reversal_of": payment.reversal_of_id or "",
                "package": payment.package_id or "",
            }
        )
    return rows


# --- Istruzioni di pagamento (fase 8) ------------------------------------------------------


def instructions_for_studio(ctx: TenantContext) -> PaymentInstructions | None:
    """Le istruzioni del proprio studio, per titolare e insegnanti. Mai da un id nella richiesta."""
    if ctx.studio_id is None or not (ctx.is_owner or ctx.is_teacher):
        return None
    return PaymentInstructions.objects.filter(studio_id=ctx.studio_id).first()


def instructions_for_open_packages(
    ctx: TenantContext,
) -> list[tuple[PaymentInstructions, list[int]]]:
    """Le istruzioni degli studi in cui chi chiama ha un pacchetto ancora da pagare, con gli
    studenti (visibili a chi chiama) che ce l'hanno: il portale mostra le istruzioni accanto
    al pacchetto di quello studente e a nessun altro.

    Per un genitore con figli in due studi sono due voci. Due query in tutto (le coppie
    studio-studente dei pacchetti aperti, poi le istruzioni), qualunque sia il numero di
    pacchetti. Studi senza istruzioni, o con la riga vuota, non compaiono.
    """
    from .services import has_content  # services importa selectors: evita il ciclo

    pairs = open_packages(ctx).values_list("student__studio_id", "student_id").distinct()
    students_by_studio: dict[int, set[int]] = {}
    for studio_id, student_id in pairs:
        students_by_studio.setdefault(studio_id, set()).add(student_id)
    rows = PaymentInstructions.objects.filter(studio_id__in=students_by_studio).select_related(
        "studio"
    )
    return [
        (row, sorted(students_by_studio[row.studio_id]))
        for row in rows.order_by("studio_id")
        if has_content(row)
    ]


# --- Ricevute (fase 8) ---------------------------------------------------------------------


def receipts_for(ctx: TenantContext) -> QuerySet[Receipt]:
    """Le ricevute emesse che chi chiama può vedere, e solo quelle.

    Come per i pagamenti il filtro passa da `scope` (qui con RECEIPT_PATHS): il titolare vede lo
    studio, l'insegnante i propri studenti, il genitore e lo studente adulto solo il proprio.
    Pagamento e studente sono nello stesso select_related e lo storno è un'annotazione
    (`payment_reversed_amount`): nessuna query per riga.
    """
    return scope(
        Receipt.objects.select_related("payment__student").annotate(
            payment_reversed_amount=_reversed_total("payment_id")
        ),
        ctx,
        RECEIPT_PATHS,
    )


# --- Conto di pagamento dello studio (fase 9) -----------------------------------------------


def payment_account_for(ctx: TenantContext) -> StudioPaymentAccount | None:
    """Il conto del proprio studio, per titolare e insegnanti. Mai da un id nella richiesta."""
    if ctx.studio_id is None or not (ctx.is_owner or ctx.is_teacher):
        return None
    return StudioPaymentAccount.objects.filter(studio_id=ctx.studio_id).first()


def attention_items(account: StudioPaymentAccount, limit: int = 20) -> list[dict[str, Any]]:
    """Gli ultimi eventi del conto che non combaciano col registro (solo id, tipo, importo).

    Mai il contenuto dell'evento: lo studio vede che c'è qualcosa da controllare su Stripe, non i
    dati di chi ha pagato.
    """
    rows = WebhookEvent.objects.filter(
        stripe_account_id=account.stripe_account_id,
        outcome=WebhookEvent.Outcome.NEEDS_ATTENTION,
    ).order_by("-received_at", "-id")[:limit]
    items = []
    for row in rows:
        obj = (row.payload.get("data") or {}).get("object") or {}
        cents = obj.get("amount_total", obj.get("amount"))
        items.append(
            {
                "id": row.pk,
                "kind": row.attention_kind,
                "received_at": row.received_at,
                "amount": (Decimal(cents) / 100).quantize(Decimal("0.01"))
                if cents is not None
                else None,
            }
        )
    return items
