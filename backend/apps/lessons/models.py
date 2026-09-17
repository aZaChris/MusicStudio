from django.db import models, transaction

from apps.packages.models import Package
from apps.students.models import Student
from apps.studios.models import Teacher


class Lesson(models.Model):
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

    def __str__(self) -> str:
        return f"{self.student} @ {self.start_time:%Y-%m-%d %H:%M}"

    @transaction.atomic
    def mark_completed(self, note: str = "") -> None:
        """Idempotent: only the first transition into COMPLETED decrements the
        linked package. Constitution Principle III business-critical path."""
        if self.status == self.Status.COMPLETED:
            return

        self.status = self.Status.COMPLETED
        if note:
            self.notes = note
        self.save(update_fields=["status", "notes", "updated_at"])

        if self.package_id is not None:
            locked_package = Package.objects.select_for_update().get(pk=self.package_id)
            if locked_package.lessons_remaining > 0:
                locked_package.lessons_remaining -= 1
                locked_package.save(update_fields=["lessons_remaining", "updated_at"])

    def cancel(self, status: str) -> None:
        if status not in (self.Status.CANCELLED, self.Status.NO_SHOW):
            raise ValueError("status must be 'cancelled' or 'no_show'")
        if self.status == self.Status.COMPLETED:
            return
        self.status = status
        self.save(update_fields=["status", "updated_at"])
