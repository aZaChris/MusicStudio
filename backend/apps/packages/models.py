from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.students.models import Student


class Package(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        COMPLETED = "completed", "Completed"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="packages")
    total_lessons = models.PositiveSmallIntegerField()
    # System-managed: set by packages.services.create_package, decremented only by
    # lessons.services.complete_lesson. Read-only through the API.
    lessons_remaining = models.PositiveSmallIntegerField()
    purchase_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-purchase_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(lessons_remaining__gte=0)
                & models.Q(lessons_remaining__lte=models.F("total_lessons")),
                name="package_remaining_within_total",
            )
        ]
        indexes = [
            # "Active package of a student": newest package that still has lessons left.
            models.Index(
                fields=["student", "-purchase_date"],
                name="package_active_by_student_idx",
                condition=models.Q(lessons_remaining__gt=0),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} — {self.lessons_remaining}/{self.total_lessons}"

    def tenant_keys(self) -> tuple[int, int]:
        return self.student.studio_id, self.student.teacher_id

    @property
    def status(self) -> str:
        if self.expiry_date and self.expiry_date < timezone.localdate():
            return self.Status.EXPIRED
        if self.lessons_remaining == 0:
            return self.Status.COMPLETED
        return self.Status.ACTIVE

    @property
    def is_low(self) -> bool:
        threshold: int = getattr(settings, "PACKAGE_LOW_THRESHOLD", 2)
        return 0 < self.lessons_remaining <= threshold
