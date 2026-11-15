"""Letture dei pacchetti (selectors). Le scritture stanno in services.py (ADR-002)."""

from django.db.models import QuerySet

from apps.common.scoping import packages_visible_to
from apps.common.tenancy import TenantContext

from .models import Package


def packages_for(ctx: TenantContext) -> QuerySet[Package]:
    """Pacchetti visibili a chi chiama. Il filtro per studio e ruolo sta in `packages_visible_to`:
    nessuna view filtra da sé (docs/learning/concetti/multi-tenancy.md)."""
    return packages_visible_to(ctx).select_related("student")
