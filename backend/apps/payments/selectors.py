"""Letture dei pagamenti (solo query, nessuna scrittura).

Regola del progetto: le scritture stanno in services.py, le letture qui
(docs/learning/concetti/service-layer-e-modular-monolith.md, ADR-002).
"""

from django.db.models import QuerySet

from apps.common.scoping import STUDENT_CHILD_PATHS, scope
from apps.common.tenancy import TenantContext

from .models import Payment


def payments_for(ctx: TenantContext) -> QuerySet[Payment]:
    """I pagamenti che l'utente può vedere, e solo quelli.

    Il filtro per studio/insegnante passa SEMPRE da `scope`: è l'unico punto che isola i
    tenant (docs/learning/concetti/isolamento-tenant-e-bola.md, ADR-010). Il pagamento non ha
    un proprio studio: eredita quello dello studente, da qui STUDENT_CHILD_PATHS.
    `select_related("student")` evita una query per riga (concetti/orm-e-problema-n-piu-1.md).
    """
    return scope(Payment.objects.select_related("student"), ctx, STUDENT_CHILD_PATHS)
