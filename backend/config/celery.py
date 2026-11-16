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
    # Studio payment accounts (phase 9): no Stripe events for v2 account state, so re-read them.
    "refresh-payment-accounts": {
        "task": "apps.payments.tasks.refresh_payment_accounts",
        "schedule": crontab(minute=37),
    },
    # Processed Stripe events older than 90 days are only extra data to keep (ADR-039).
    "purge-old-webhook-events": {
        "task": "apps.payments.tasks.purge_old_webhook_events",
        "schedule": crontab(hour=3, minute=27),
    },
    # Revocation tables only need rows until the refresh token would expire (ADR-018).
    "purge-expired-tokens": {
        "task": "apps.accounts.tasks.purge_expired_tokens",
        "schedule": crontab(hour=3, minute=17),
    },
    # Retention periods of ADR-032: old archived students, payments, audit, unconfirmed sign-ups.
    "run-retention": {
        "task": "apps.privacy.tasks.run_retention",
        "schedule": crontab(hour=3, minute=42),
    },
}
