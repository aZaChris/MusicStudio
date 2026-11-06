"""Read queries for payments."""

from django.db.models import QuerySet

from apps.common.scoping import STUDENT_CHILD_PATHS, scope
from apps.common.tenancy import TenantContext

from .models import Payment


def payments_for(ctx: TenantContext) -> QuerySet[Payment]:
    return scope(Payment.objects.select_related("student"), ctx, STUDENT_CHILD_PATHS)
