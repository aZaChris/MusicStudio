"""Lesson reminders through a transactional outbox (ADR-015, supersedes ADR-008).

1. The sweep (every 15 min) finds lessons ~24h away and, in one transaction, marks the
   lesson as swept and inserts one `ReminderDelivery` per linked parent. Re-running it,
   or two overlapping sweeps, cannot duplicate rows: `UNIQUE (lesson, parent)`.
2. Each delivery is sent by its own task. A delivery is claimed with a conditional
   UPDATE (pending, or "sending" whose lease expired), sent, then marked sent. Failures go
   back to pending and the task retries with exponential backoff.

Guarantee: at least once, de-duplicated per (lesson, parent). The only duplicate window
left is a crash after the SMTP server accepted the email and before we mark it sent —
exactly-once is impossible with SMTP; this window is milliseconds instead of "forever".
"""

import datetime
import logging

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Prefetch, Q, QuerySet
from django.template.loader import render_to_string
from django.utils import timezone

from apps.lessons.models import Lesson
from apps.students.models import ParentStudentLink

from .models import ReminderDelivery

logger = logging.getLogger(__name__)

REMINDER_WINDOW_START = datetime.timedelta(hours=23, minutes=45)
REMINDER_WINDOW_END = datetime.timedelta(hours=24)
LEASE = datetime.timedelta(minutes=10)
MAX_ATTEMPTS = 5


class DeliveryFailed(Exception):
    """The email could not be sent; the delivery is back to pending for a retry."""


def due_lessons(now: datetime.datetime) -> QuerySet[Lesson]:
    return Lesson.objects.filter(
        status=Lesson.Status.SCHEDULED,
        start_time__gte=now + REMINDER_WINDOW_START,
        start_time__lt=now + REMINDER_WINDOW_END,
        reminder_sent_at__isnull=True,
    ).prefetch_related(
        Prefetch("student__parentstudentlink_set", queryset=ParentStudentLink.objects.all())
    )


def enqueue_due_reminders(now: datetime.datetime | None = None) -> int:
    """Record the deliveries for every due lesson. Returns how many lessons were swept."""
    now = now or timezone.now()
    swept = 0
    for lesson in due_lessons(now):
        with transaction.atomic():
            claimed = Lesson.objects.filter(pk=lesson.pk, reminder_sent_at__isnull=True).update(
                reminder_sent_at=now
            )
            if not claimed:
                continue  # an overlapping sweep got there first
            ReminderDelivery.objects.bulk_create(
                [
                    ReminderDelivery(lesson_id=lesson.pk, parent_id=link.parent_id)
                    for link in lesson.student.parentstudentlink_set.all()
                ],
                ignore_conflicts=True,
            )
        swept += 1
    return swept


def deliveries_to_send(now: datetime.datetime | None = None) -> list[int]:
    """Pending deliveries, plus those whose sender died while holding the lease."""
    now = now or timezone.now()
    stale = Q(status=ReminderDelivery.Status.SENDING, claimed_at__lt=now - LEASE)
    return list(
        ReminderDelivery.objects.filter(Q(status=ReminderDelivery.Status.PENDING) | stale)
        .order_by("id")
        .values_list("id", flat=True)[:500]
    )


def _claim(delivery_id: int, now: datetime.datetime) -> bool:
    claimable = Q(status=ReminderDelivery.Status.PENDING) | Q(
        status=ReminderDelivery.Status.SENDING, claimed_at__lt=now - LEASE
    )
    return (
        ReminderDelivery.objects.filter(claimable, pk=delivery_id).update(
            status=ReminderDelivery.Status.SENDING, claimed_at=now, attempts=F("attempts") + 1
        )
        == 1
    )


def send_delivery(delivery_id: int) -> str:
    """Claim, send, mark. Returns the outcome; raises DeliveryFailed on a send error."""
    now = timezone.now()
    if not _claim(delivery_id, now):
        return "not-claimable"  # already sent, or someone else holds a fresh lease
    delivery = ReminderDelivery.objects.select_related("lesson__student", "parent__user").get(
        pk=delivery_id
    )
    if delivery.lesson.status != Lesson.Status.SCHEDULED:
        _set(delivery_id, ReminderDelivery.Status.SKIPPED)
        return "skipped"
    recipient = delivery.parent.user
    body = render_to_string(
        f"notifications/reminder_email_{recipient.preferred_language}.txt",
        {
            "student_name": delivery.lesson.student.full_name,
            "start_time": delivery.lesson.start_time,
        },
    )
    try:
        send_mail(
            subject="Upcoming lesson reminder — MusicStudio",
            message=body,
            from_email=None,
            recipient_list=[recipient.email],
        )
    except Exception as exc:
        _set(delivery_id, ReminderDelivery.Status.PENDING, error=str(exc))
        raise DeliveryFailed(str(exc)) from exc
    ReminderDelivery.objects.filter(pk=delivery_id).update(
        status=ReminderDelivery.Status.SENT, sent_at=timezone.now(), last_error=""
    )
    return "sent"


def give_up(delivery_id: int, error: str) -> None:
    logger.error("Reminder delivery %s failed permanently: %s", delivery_id, error)
    _set(delivery_id, ReminderDelivery.Status.FAILED, error=error)


def _set(delivery_id: int, status: str, *, error: str = "") -> None:
    ReminderDelivery.objects.filter(pk=delivery_id).update(status=status, last_error=error[:1000])
