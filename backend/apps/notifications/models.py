"""Tabella dell'outbox dei promemoria (ADR-015). La logica sta in services.py."""

from django.db import models

from apps.lessons.models import Lesson
from apps.students.models import ParentAccount


class ReminderDelivery(models.Model):
    """Una email di promemoria da inviare: la outbox transazionale (ADR-015).

    Il giro periodico (sweep) si limita a *registrare* cosa va inviato; l'invio avviene in un
    task a parte, con i tentativi. `UNIQUE (lesson, parent)` rende innocuo rieseguire lo sweep.
    Spiegazione: docs/learning/concetti/task-celery-idempotenti.md.
    """

    class Status(models.TextChoices):
        # pending = da inviare; sending = preso in carico da un worker; sent = inviato;
        # failed = tentativi esauriti; skipped = la lezione non è più in programma.
        PENDING = "pending", "Pending"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="reminders")
    parent = models.ForeignKey(ParentAccount, on_delete=models.CASCADE, related_name="reminders")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    # Lease (concessione a tempo): un worker che ha preso in carico l'invio e poi muore lo lascia
    # in "sending"; passato LEASE un altro può riprenderlo (at-least-once, ADR-015).
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Il vincolo di unicità è ciò che impedisce i doppioni, anche con due sweep sovrapposti.
        constraints = [
            models.UniqueConstraint(fields=["lesson", "parent"], name="unique_reminder_delivery")
        ]
        indexes = [models.Index(fields=["status"], name="reminder_status_idx")]

    def __str__(self) -> str:
        return f"{self.lesson} → {self.parent} ({self.status})"
