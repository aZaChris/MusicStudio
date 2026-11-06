from django.db import models

from apps.lessons.models import Lesson
from apps.students.models import ParentAccount


class ReminderDelivery(models.Model):
    """One reminder email to send: the transactional outbox (ADR-015).

    The sweep only *records* what must be sent; sending happens in its own task, with
    retries. `UNIQUE (lesson, parent)` makes re-running the sweep harmless.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="reminders")
    parent = models.ForeignKey(ParentAccount, on_delete=models.CASCADE, related_name="reminders")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    # Lease: a worker that claimed the delivery and died leaves it in "sending"; after
    # LEASE it can be claimed again (at-least-once, ADR-015).
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["lesson", "parent"], name="unique_reminder_delivery")
        ]
        indexes = [models.Index(fields=["status"], name="reminder_status_idx")]

    def __str__(self) -> str:
        return f"{self.lesson} → {self.parent} ({self.status})"
