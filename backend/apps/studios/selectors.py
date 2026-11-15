"""Letture di studio e insegnanti, riservate al titolare dello studio (ADR-010, ADR-011)."""

from django.db.models import Count, QuerySet

from apps.common.tenancy import TenantContext

from .models import Studio, Teacher


def _owner_studio_id(ctx: TenantContext) -> int | None:
    # Solo il titolare ha uno studio da gestire: per tutti gli altri ruoli non c'è nulla da
    # mostrare, e le funzioni sotto restituiscono vuoto invece di filtrare male.
    return ctx.studio_id if ctx.is_owner else None


def studio_for_owner(ctx: TenantContext) -> Studio | None:
    # Il numero di insegnanti si conta nella stessa query (annotate): niente N+1.
    studio_id = _owner_studio_id(ctx)
    if studio_id is None:
        return None
    return Studio.objects.annotate(teacher_count=Count("teachers")).filter(pk=studio_id).first()


def teachers_for_owner(ctx: TenantContext) -> QuerySet[Teacher]:
    # `select_related("user")` perché il serializer mostra l'email dell'utente.
    studio_id = _owner_studio_id(ctx)
    if studio_id is None:
        return Teacher.objects.none()
    return Teacher.objects.select_related("user").filter(studio_id=studio_id).order_by("id")
