from django.db import models

from apps.packages.models import Package
from apps.students.models import Student
from apps.studios.models import Teacher


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
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    notes = models.TextField(blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]
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
