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
    lessons_remaining = models.PositiveSmallIntegerField()
    purchase_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-purchase_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(lessons_remaining__gte=0)
                & models.Q(lessons_remaining__lte=models.F("total_lessons")),
                name="package_remaining_within_total",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student} — {self.lessons_remaining}/{self.total_lessons}"

    @property
    def status(self) -> str:
        if self.expiry_date and self.expiry_date < timezone.localdate():
            return self.Status.EXPIRED
        if self.lessons_remaining == 0:
            return self.Status.COMPLETED
        return self.Status.ACTIVE

    @property
    def is_low(self) -> bool:
        threshold = getattr(settings, "PACKAGE_LOW_THRESHOLD", 2)
        return 0 < self.lessons_remaining <= threshold
