import datetime

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators
from django.db import models

from apps.packages.models import Package
from apps.students.models import Student
from apps.studios.models import Teacher


class TsTzRange(models.Func):
    """SQL `tstzrange(start, end, '[)')`: a half-open time interval."""

    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


# Statuses that occupy a slot. Cancelled and no-show lessons free it.
ACTIVE_STATUSES = ("scheduled", "completed")


class Lesson(models.Model):
    """A lesson slot. State transitions live in lessons.services (ADR-002)."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No-show"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="lessons")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="lessons")
    package = models.ForeignKey(
        Package, on_delete=models.SET_NULL, null=True, blank=True, related_name="lessons"
    )
    start_time = models.DateTimeField()
    # Stored, not computed in SQL: `timestamptz + interval` is STABLE, not IMMUTABLE, so it
    # cannot appear in the exclusion constraint's index expression (ADR-009).
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    notes = models.TextField(blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="lesson_end_after_start",
            ),
            # The database itself refuses overlapping active lessons, even when two
            # requests insert at the same moment (an app-level check would race).
            ExclusionConstraint(
                name="lesson_no_teacher_overlap",
                expressions=[
                    (TsTzRange("start_time", "end_time", RangeBoundary()), RangeOperators.OVERLAPS),
                    ("teacher", RangeOperators.EQUAL),
                ],
                condition=models.Q(status__in=ACTIVE_STATUSES),
            ),
            ExclusionConstraint(
                name="lesson_no_student_overlap",
                expressions=[
                    (TsTzRange("start_time", "end_time", RangeBoundary()), RangeOperators.OVERLAPS),
                    ("student", RangeOperators.EQUAL),
                ],
                condition=models.Q(status__in=ACTIVE_STATUSES),
            ),
        ]
        indexes = [
            # Weekly agenda / upcoming / dashboard: WHERE teacher_id = ? AND start_time range.
            models.Index(fields=["teacher", "start_time"], name="lesson_teacher_start_idx"),
            # Reminder sweep: only the small set of scheduled, not-yet-reminded lessons.
            models.Index(
                fields=["start_time"],
                name="lesson_reminder_due_idx",
                condition=models.Q(status="scheduled", reminder_sent_at__isnull=True),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} @ {self.start_time:%Y-%m-%d %H:%M}"

    def tenant_keys(self) -> tuple[int, int]:
        return self.student.studio_id, self.teacher_id

    @property
    def duration_minutes(self) -> int:
        # Compare in UTC: subtracting two datetimes that share a tzinfo is wall-clock math.
        elapsed = self.end_time.astimezone(datetime.UTC) - self.start_time.astimezone(datetime.UTC)
        return int(elapsed.total_seconds() // 60)
