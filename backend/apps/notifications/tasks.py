"""Reminder tasks. The logic and its guarantees live in services.py (ADR-015)."""

from typing import Any

from celery import shared_task

from . import services


@shared_task
def send_lesson_reminders() -> int:
    """Celery Beat, every 15 minutes: record due deliveries, then dispatch pending ones."""
    services.enqueue_due_reminders()
    pending = services.deliveries_to_send()
    for delivery_id in pending:
        send_reminder_delivery.delay(delivery_id)
    return len(pending)


@shared_task(bind=True, max_retries=services.MAX_ATTEMPTS - 1)
def send_reminder_delivery(self: Any, delivery_id: int) -> str:
    try:
        return services.send_delivery(delivery_id)
    except services.DeliveryFailed as exc:
        if self.request.retries >= self.max_retries:
            services.give_up(delivery_id, str(exc))
            return "failed"
        # Exponential backoff: 30 s, 60 s, 120 s, 240 s.
        raise self.retry(exc=exc, countdown=30 * 2**self.request.retries) from exc
