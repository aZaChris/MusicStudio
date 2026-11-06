import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("musicstudio")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Creates one ReminderDelivery per (lesson, parent) and dispatches pending ones.
    "send-lesson-reminders": {
        "task": "apps.notifications.tasks.send_lesson_reminders",
        "schedule": crontab(minute="*/15"),
    },
    # Safety net for lost Stripe webhooks (ADR-014).
    "reconcile-open-checkouts": {
        "task": "apps.payments.tasks.reconcile_open_checkouts",
        "schedule": crontab(minute=7),
    },
}
