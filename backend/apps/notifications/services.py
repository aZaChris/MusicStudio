"""Lesson reminder sweep.

Delivery is **at most once** per lesson (ADR-008): each lesson is claimed with a
conditional UPDATE before any email is sent. Two overlapping sweeps can both select the
same lesson, but only one of them wins the claim. If the process dies after the claim and
before sending, that reminder is lost rather than duplicated — a deliberate trade-off.
"""

import datetime
import logging

from django.core.mail import send_mail
from django.db.models import Prefetch, QuerySet
from django.template.loader import render_to_string
from django.utils import timezone

from apps.lessons.models import Lesson
from apps.students.models import ParentStudentLink

logger = logging.getLogger(__name__)

REMINDER_WINDOW_START = datetime.timedelta(hours=23, minutes=45)
REMINDER_WINDOW_END = datetime.timedelta(hours=24)


def due_lessons(now: datetime.datetime) -> QuerySet[Lesson]:
    return (
        Lesson.objects.filter(
            status=Lesson.Status.SCHEDULED,
            start_time__gte=now + REMINDER_WINDOW_START,
            start_time__lt=now + REMINDER_WINDOW_END,
            reminder_sent_at__isnull=True,
        )
        .select_related("student")
        .prefetch_related(
            Prefetch(
                "student__parentstudentlink_set",
                queryset=ParentStudentLink.objects.select_related("parent__user"),
            )
        )
    )


def claim_lesson(lesson_id: int, now: datetime.datetime) -> bool:
    """Atomically mark a lesson as reminded. True only for the caller that won the claim."""
    updated = Lesson.objects.filter(pk=lesson_id, reminder_sent_at__isnull=True).update(
        reminder_sent_at=now
    )
    return updated == 1


def send_due_reminders(now: datetime.datetime | None = None) -> int:
    """Remind linked parents of lessons ~24h away. Returns the number of lessons reminded."""
    now = now or timezone.now()
    reminded = 0
    for lesson in due_lessons(now):
        if not claim_lesson(lesson.pk, now):
            continue  # another sweep got there first
        for link in lesson.student.parentstudentlink_set.all():
            recipient = link.parent.user
            body = render_to_string(
                f"notifications/reminder_email_{recipient.preferred_language}.txt",
                {"student_name": lesson.student.full_name, "start_time": lesson.start_time},
            )
            try:
                send_mail(
                    subject="Upcoming lesson reminder — MusicStudio",
                    message=body,
                    from_email=None,
                    recipient_list=[recipient.email],
                )
            except Exception:
                # At-most-once: log and move on; the claim is not rolled back.
                logger.exception("Reminder email failed for lesson %s", lesson.pk)
        reminded += 1
    return reminded
