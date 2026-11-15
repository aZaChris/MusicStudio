"""Task Celery dei promemoria. La logica e le sue garanzie stanno in services.py (ADR-015)."""

from typing import Any

from celery import shared_task

from . import services


@shared_task
def send_lesson_reminders() -> int:
    """Celery Beat, ogni 15 minuti: registra gli invii dovuti, poi mette in coda quelli pendenti."""
    services.enqueue_due_reminders()
    pending = services.deliveries_to_send()
    for delivery_id in pending:
        send_reminder_delivery.delay(delivery_id)
    return len(pending)


@shared_task(bind=True, max_retries=services.MAX_ATTEMPTS - 1)
def send_reminder_delivery(self: Any, delivery_id: int) -> str:
    # Un task per ogni invio: un invio che fallisce si ripete da solo, senza fermare gli altri.
    # Affidabilità dei task Celery: ADR-016.
    try:
        return services.send_delivery(delivery_id)
    except services.DeliveryFailed as exc:
        if self.request.retries >= self.max_retries:
            services.give_up(delivery_id, str(exc))
            return "failed"
        # Backoff esponenziale: 30 s, 60 s, 120 s, 240 s. Dopo l'ultimo tentativo si rinuncia.
        raise self.retry(exc=exc, countdown=30 * 2**self.request.retries) from exc
