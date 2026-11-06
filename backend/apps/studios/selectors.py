"""Read queries for studios (studio-owner only)."""

from django.db.models import Count, QuerySet

from apps.common.tenancy import TenantContext

from .models import Studio, Teacher


def _owner_studio_id(ctx: TenantContext) -> int | None:
    return ctx.studio_id if ctx.is_owner else None


def studio_for_owner(ctx: TenantContext) -> Studio | None:
    studio_id = _owner_studio_id(ctx)
    if studio_id is None:
        return None
    return Studio.objects.annotate(teacher_count=Count("teachers")).filter(pk=studio_id).first()


def teachers_for_owner(ctx: TenantContext) -> QuerySet[Teacher]:
    studio_id = _owner_studio_id(ctx)
    if studio_id is None:
        return Teacher.objects.none()
    return Teacher.objects.select_related("user").filter(studio_id=studio_id).order_by("id")
