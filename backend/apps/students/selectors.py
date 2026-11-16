"""Letture degli studenti (selectors).

L'elenco prima faceva 2 query in più per ogni studente (pacchetto attivo e ultimo pagamento):
22 query per 10 studenti. Ora entrambi si caricano per tutta la pagina in una volta, quindi il
numero di query resta costante (audit G2).
Spiegazione: docs/learning/concetti/orm-e-problema-n-piu-1.md.
"""

from django.db.models import OuterRef, Prefetch, QuerySet, Subquery

from apps.common.scoping import students_visible_to
from apps.common.tenancy import TenantContext
from apps.packages.models import Package
from apps.payments.models import Payment
from apps.payments.selectors import not_fully_reversed, with_reversals

from .models import ACTIVE_PACKAGES_ATTR, Student


def active_packages_prefetch(lookup: str = "packages") -> Prefetch:
    # Un'unica query per i pacchetti con lezioni rimaste di tutti gli studenti della pagina.
    # Il risultato finisce in `student.active_packages`, già ordinato dal più recente.
    return Prefetch(
        lookup,
        queryset=Package.objects.filter(lessons_remaining__gt=0).order_by("-purchase_date", "-id"),
        to_attr=ACTIVE_PACKAGES_ATTR,
    )


def latest_payment_status_subquery() -> Subquery:
    # Sottoquery correlata: lo stato dell'ultimo pagamento entra come colonna della stessa query
    # degli studenti, senza una query per riga.
    # Le righe di storno e i pagamenti stornati per intero non contano per lo stato (fase 8);
    # un rimborso parziale lascia il pagamento valido (fase 9, ADR-038).
    return Subquery(
        with_reversals(Payment.objects.filter(student=OuterRef("pk")))
        .filter(not_fully_reversed())
        .exclude(status=Payment.Status.REVERSAL)
        .order_by("-date", "-id")
        .values("status")[:1]
    )


def students_for(ctx: TenantContext) -> QuerySet[Student]:
    """Elenco: gli studenti visibili a chi chiama, con pacchetto attivo e stato dell'ultimo
    pagamento già caricati. Il filtro per studio e ruolo è in `students_visible_to`."""
    return (
        students_visible_to(ctx)
        .annotate(latest_payment_status=latest_payment_status_subquery())
        .prefetch_related(active_packages_prefetch())
    )
