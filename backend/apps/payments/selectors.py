"""Letture dei pagamenti (solo query, nessuna scrittura).

Regola del progetto: le scritture stanno in services.py, le letture qui
(docs/learning/concetti/service-layer-e-modular-monolith.md, ADR-002).
"""

from django.db.models import Exists, OuterRef, QuerySet

from apps.common.scoping import STUDENT_CHILD_PATHS, packages_visible_to, scope
from apps.common.tenancy import TenantContext
from apps.packages.models import Package

from .models import Payment


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
