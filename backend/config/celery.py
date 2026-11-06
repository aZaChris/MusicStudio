import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("musicstudio")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "send-lesson-reminders": {
        "task": "apps.notifications.tasks.send_lesson_reminders",
        "schedule": crontab(minute="*/15"),
    },
}
