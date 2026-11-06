"""Read queries for lessons and the teacher dashboard."""

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
    """`?week=YYYY-MM-DD` (any day of the week); today when absent. Bad input → 400."""
    if not value:
        return timezone.localdate()
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({"week": "Expected a date in YYYY-MM-DD format."}) from exc


def week_bounds(anchor: datetime.date) -> tuple[datetime.datetime, datetime.datetime]:
    """Monday 00:00 → next Monday 00:00 in the studio's timezone, as aware datetimes.

    A range on the raw column (instead of `start_time__date`) lets PostgreSQL use the
    (teacher, start_time) index.
    """
    monday = anchor - datetime.timedelta(days=anchor.weekday())
    start = timezone.make_aware(datetime.datetime.combine(monday, datetime.time.min))
    return start, start + datetime.timedelta(days=7)


def lessons_for(ctx: TenantContext) -> QuerySet[Lesson]:
    return scope(Lesson.objects.select_related("student"), ctx, LESSON_PATHS)


def lessons_in_week(ctx: TenantContext, anchor: datetime.date) -> QuerySet[Lesson]:
    start, end = week_bounds(anchor)
    return lessons_for(ctx).filter(start_time__gte=start, start_time__lt=end)


def upcoming_lessons_for(ctx: TenantContext, limit: int = 3) -> QuerySet[Lesson]:
    return (
        lessons_for(ctx)
        .filter(status=Lesson.Status.SCHEDULED, start_time__gte=timezone.now())
        .order_by("start_time")[:limit]
    )


def lessons_of_student(student: Student) -> QuerySet[Lesson]:
    return student.lessons.select_related("student").order_by("-start_time")


def low_package_students_for(ctx: TenantContext) -> QuerySet[Student]:
    """Active students whose active package has 1..threshold lessons left — one query."""
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
    """Five queries regardless of studio size (was 5 + one per student)."""
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
