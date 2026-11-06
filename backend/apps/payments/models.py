from django.db import models

from apps.packages.models import Package
from apps.students.models import Student


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"
        MANUAL_ENTRY = "manual_entry", "Manual entry"

    class Status(models.TextChoices):
        PAID = "paid", "Paid"
        PENDING = "pending", "Pending"
        OVERDUE = "overdue", "Overdue"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="payments")
    package = models.ForeignKey(
        Package, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    date = models.DateField()
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            # Latest payment of a student (roster subquery) and the student's history.
            models.Index(fields=["student", "-date"], name="payment_student_date_idx"),
            # Dashboard "pending payments" count and the ?status= filter.
            models.Index(fields=["status"], name="payment_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.student} — {self.amount} ({self.status})"

    def tenant_keys(self) -> tuple[int, int]:
        return self.student.studio_id, self.student.teacher_id

    def clean(self) -> None:
        # Same rule as the API, for the Django admin (which calls full_clean()).
        from .services import ensure_package_matches_student

        if self.student_id is not None:
            ensure_package_matches_student(self.student, self.package)
