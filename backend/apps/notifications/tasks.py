from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from config.celery import app

REMINDER_WINDOW_START = timezone.timedelta(hours=23, minutes=45)
REMINDER_WINDOW_END = timezone.timedelta(hours=24)


@app.task
def send_lesson_reminders() -> int:
    """Celery Beat sweep (every 15 min): reminds parents of lessons ~24h out.

    Idempotent via `reminder_sent_at` — safe to re-run the same window twice.
    Only SCHEDULED lessons are considered, so a cancelled/no_show lesson is
    skipped even if it falls inside the window.
    """
    from apps.lessons.models import Lesson  # avoid app-loading import cycle

    now = timezone.now()
    window_start = now + REMINDER_WINDOW_START
    window_end = now + REMINDER_WINDOW_END

    due_lessons = Lesson.objects.filter(
        status=Lesson.Status.SCHEDULED,
        start_time__gte=window_start,
        start_time__lt=window_end,
        reminder_sent_at__isnull=True,
    ).select_related("student")

    sent = 0
    for lesson in due_lessons:
        links = lesson.student.parentstudentlink_set.select_related("parent__user")
        for link in links:
            recipient = link.parent.user
            template = f"notifications/reminder_email_{recipient.preferred_language}.txt"
            body = render_to_string(
                template,
                {"student_name": lesson.student.full_name, "start_time": lesson.start_time},
            )
            send_mail(
                subject="Upcoming lesson reminder — MusicStudio",
                message=body,
                from_email=None,
                recipient_list=[recipient.email],
            )
        lesson.reminder_sent_at = now
        lesson.save(update_fields=["reminder_sent_at"])
        sent += 1

    return sent
