"""Read queries for students.

The roster used to run 2 extra queries per student (active package + latest payment):
22 queries for 10 students. Here both are fetched for the whole page at once, so the
count stays constant (audit G2).
"""

from django.db.models import OuterRef, Prefetch, QuerySet, Subquery

from apps.common.scoping import students_visible_to
from apps.common.tenancy import TenantContext
from apps.packages.models import Package
from apps.payments.models import Payment

from .models import ACTIVE_PACKAGES_ATTR, Student


def active_packages_prefetch(lookup: str = "packages") -> Prefetch:
    return Prefetch(
        lookup,
        queryset=Package.objects.filter(lessons_remaining__gt=0).order_by("-purchase_date", "-id"),
        to_attr=ACTIVE_PACKAGES_ATTR,
    )


def latest_payment_status_subquery() -> Subquery:
    return Subquery(
        Payment.objects.filter(student=OuterRef("pk")).order_by("-date", "-id").values("status")[:1]
    )


def students_for(ctx: TenantContext) -> QuerySet[Student]:
    """Roster: scoped students with active package and latest payment status preloaded."""
    return (
        students_visible_to(ctx)
        .annotate(latest_payment_status=latest_payment_status_subquery())
        .prefetch_related(active_packages_prefetch())
    )
