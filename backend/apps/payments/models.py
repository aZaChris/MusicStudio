import uuid

from django.conf import settings
from django.db import models

from apps.packages.models import Package
from apps.students.models import Student


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"
        MANUAL_ENTRY = "manual_entry", "Manual entry"
        CARD = "card", "Online (Stripe)"

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
    # Set only for online payments. OneToOne = at most one payment per checkout attempt,
    # enforced by the database even if a webhook is processed twice (ADR-014).
    checkout = models.OneToOneField(
        "payments.CheckoutSession",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payment",
    )
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


class CheckoutSession(models.Model):
    """One online payment attempt for a package (a Stripe Checkout Session) — ADR-013."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"

    # UUID: used in the Stripe idempotency key and metadata, not guessable in URLs.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="checkouts")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    stripe_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    url = models.URLField(max_length=2000, blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["package", "status"], name="checkout_package_status_idx"),
            # Hourly reconciliation: open attempts past their expiry.
            models.Index(
                fields=["expires_at"],
                name="checkout_open_expiry_idx",
                condition=models.Q(status="open"),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.package} — {self.status}"


class WebhookEvent(models.Model):
    """A Stripe notification, stored once by its event id (ADR-014).

    The unique `stripe_event_id` turns Stripe's retries and duplicates into no-ops;
    `processed_at` makes the processing task idempotent.
    """

    stripe_event_id = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=100)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.type} {self.stripe_event_id}"
