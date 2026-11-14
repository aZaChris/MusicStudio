"""Letture di lezioni e dashboard dell'insegnante (solo query, nessuna scrittura).

Le scritture stanno in services.py (docs/learning/concetti/service-layer-e-modular-monolith.md,
ADR-002). Il numero di query è tenuto sotto controllo dai test sul budget di query
(docs/learning/concetti/orm-e-problema-n-piu-1.md).
"""

import datetime
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import OuterRef, QuerySet, Subquery
from django.utils import timezone

from apps.common.scoping import LESSON_PATHS, STUDENT_CHILD_PATHS, scope, students_visible_to
from apps.common.tenancy import TenantContext
from apps.packages.models import Package
from apps.payments.models import Payment
from apps.students.models import Student

from .models import Lesson


def parse_week(value: str | None) -> datetime.date:
    """`?week=YYYY-MM-DD` (un giorno qualsiasi della settimana); oggi se assente. Errore → 400."""
    if not value:
        return timezone.localdate()
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({"week": "Expected a date in YYYY-MM-DD format."}) from exc


def week_bounds(anchor: datetime.date) -> tuple[datetime.datetime, datetime.datetime]:
    """Da lunedì 00:00 al lunedì successivo 00:00 nel fuso dello studio, come datetime con fuso.

    Un intervallo sulla colonna grezza (invece di `start_time__date`) permette a PostgreSQL di
    usare l'indice (teacher, start_time): vedi docs/learning/concetti/indici-ed-explain.md.
    """
    monday = anchor - datetime.timedelta(days=anchor.weekday())
    start = timezone.make_aware(datetime.datetime.combine(monday, datetime.time.min))
    return start, start + datetime.timedelta(days=7)


def lessons_for(ctx: TenantContext) -> QuerySet[Lesson]:
    """Le lezioni visibili all'utente. L'isolamento tra studi passa SEMPRE da `scope`
    (docs/learning/concetti/isolamento-tenant-e-bola.md, ADR-010)."""
    return scope(Lesson.objects.select_related("student"), ctx, LESSON_PATHS)


def lessons_in_week(ctx: TenantContext, anchor: datetime.date) -> QuerySet[Lesson]:
    """Le lezioni della settimana che contiene `anchor`."""
    start, end = week_bounds(anchor)
    return lessons_for(ctx).filter(start_time__gte=start, start_time__lt=end)


def upcoming_lessons_for(ctx: TenantContext, limit: int = 3) -> QuerySet[Lesson]:
    """Le prossime lezioni in programma, dalla più vicina."""
    return (
        lessons_for(ctx)
        .filter(status=Lesson.Status.SCHEDULED, start_time__gte=timezone.now())
        .order_by("start_time")[:limit]
    )


def lessons_of_student(student: Student) -> QuerySet[Lesson]:
    """Storico delle lezioni di uno studente, dalla più recente."""
    return student.lessons.select_related("student").order_by("-start_time")


def low_package_students_for(ctx: TenantContext) -> QuerySet[Student]:
    """Studenti attivi il cui pacchetto attivo ha da 1 a "soglia" lezioni rimaste — una query.

    La soglia è PACKAGE_LOW_THRESHOLD. Il pacchetto attivo è il più recente con lezioni residue.
    """
    active_remaining = Subquery(
        Package.objects.filter(student=OuterRef("pk"), lessons_remaining__gt=0)
        .order_by("-purchase_date", "-id")
        .values("lessons_remaining")[:1]
    )
    return (
        students_visible_to(ctx)
        .filter(is_active=True)
        .annotate(active_remaining=active_remaining)
        .filter(active_remaining__gt=0, active_remaining__lte=settings.PACKAGE_LOW_THRESHOLD)
    )


def dashboard_for(ctx: TenantContext) -> dict[str, Any]:
    """Cinque query a prescindere dalla dimensione dello studio (prima: 5 più una per studente)."""
    pending_payments = scope(
        Payment.objects.filter(status=Payment.Status.PENDING), ctx, STUDENT_CHILD_PATHS
    )
    return {
        "week": list(lessons_in_week(ctx, timezone.localdate()).order_by("start_time")),
        "upcoming": list(upcoming_lessons_for(ctx)),
        "pending_payments_count": pending_payments.count(),
        "active_students_count": students_visible_to(ctx).filter(is_active=True).count(),
        "low_package_students": [
            {"id": s.pk, "full_name": s.full_name} for s in low_package_students_for(ctx)
        ],
    }
