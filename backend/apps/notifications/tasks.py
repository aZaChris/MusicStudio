from celery import shared_task

from .services import send_due_reminders


@shared_task
def send_lesson_reminders() -> int:
    """Celery Beat entry point (every 15 minutes). Logic lives in services.py."""
    return send_due_reminders()
