"""Letture dei pagamenti (solo query, nessuna scrittura).

Regola del progetto: le scritture stanno in services.py, le letture qui
(docs/learning/concetti/service-layer-e-modular-monolith.md, ADR-002).
"""

import calendar
import datetime
from decimal import Decimal
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Count, Exists, OuterRef, Q, QuerySet, Sum
from django.utils import timezone

from apps.common.exceptions import PeriodTooLong
from apps.common.scoping import STUDENT_CHILD_PATHS, packages_visible_to, scope
from apps.common.tenancy import TenantContext
from apps.packages.models import Package

from .models import Payment, PaymentInstructions


def payments_for(ctx: TenantContext) -> QuerySet[Payment]:
    """I pagamenti che l'utente può vedere, e solo quelli.

    Il filtro per studio/insegnante passa SEMPRE da `scope`: è l'unico punto che isola i
    tenant (docs/learning/concetti/isolamento-tenant-e-bola.md, ADR-010). Il pagamento non ha
    un proprio studio: eredita quello dello studente, da qui STUDENT_CHILD_PATHS.
    `select_related("student")` evita una query per riga (concetti/orm-e-problema-n-piu-1.md).
    """
    # `reversal` è nel select_related così il campo `reversed` del serializer non costa query.
    return scope(Payment.objects.select_related("student", "reversal"), ctx, STUDENT_CHILD_PATHS)


def effective_paid(qs: QuerySet[Payment]) -> QuerySet[Payment]:
    """I pagamenti che contano come denaro incassato: "paid" e non stornati (fase 8).

    Un pagamento stornato resta "paid" nel database (non si riscrive mai), ma non rende più
    pagato il pacchetto. Questa è l'unica definizione: checkout, stato dello studente e
    pacchetti aperti la usano tutti (specs/008-cash-register-receipts/research.md, R5).
    """
    return qs.filter(status=Payment.Status.PAID, reversal__isnull=True)


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


def register_rows(
    ctx: TenantContext, date_from: datetime.date, date_to: datetime.date
) -> list[dict[str, Any]]:
    """Le righe del registro per l'esportazione: una per pagamento, in ordine di data.

    Importo con segno (negativo per lo storno) e stato "visibile": un originale stornato si
    legge `reversed`. Il numero di ricevuta si aggiunge con le ricevute (storia 4).
    """
    rows = []
    for payment in _payments_in_period(ctx, date_from, date_to).order_by("date", "id"):
        is_reversal = payment.status == Payment.Status.REVERSAL
        try:
            reversed_ = payment.reversal is not None
        except ObjectDoesNotExist:
            reversed_ = False
        rows.append(
            {
                "date": payment.date,
                "receipt_number": "",
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


def instructions_for_open_packages(ctx: TenantContext) -> list[PaymentInstructions]:
    """Le istruzioni degli studi in cui chi chiama ha almeno un pacchetto ancora da pagare.

    Per un genitore con figli in due studi sono due elenchi, ognuno accanto ai pacchetti giusti.
    Due query in tutto (pacchetti aperti come sottoquery, poi le istruzioni), qualunque sia il
    numero di pacchetti. Studi senza istruzioni, o con la riga vuota, non compaiono.
    """
    from .services import has_content  # services importa selectors: evita il ciclo

    studio_ids = open_packages(ctx).values("student__studio_id")
    rows = PaymentInstructions.objects.filter(studio_id__in=studio_ids).select_related("studio")
    return [row for row in rows.order_by("studio_id") if has_content(row)]
