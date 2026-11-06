"""Read queries for packages."""

from django.db.models import QuerySet

from apps.common.scoping import packages_visible_to
from apps.common.tenancy import TenantContext

from .models import Package


def packages_for(ctx: TenantContext) -> QuerySet[Package]:
    return packages_visible_to(ctx).select_related("student")
