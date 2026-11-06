"""Lesson reminders through the outbox (US3, ADR-015)."""

import datetime

import pytest
from django.core import mail
from django.utils import timezone

from apps.common.factories import LessonFactory, ParentAccountFactory, link_parent_to_student
from apps.lessons.models import Lesson
from apps.lessons.services import cancel_lesson
from apps.notifications import services
from apps.notifications.models import ReminderDelivery
from apps.notifications.tasks import send_lesson_reminders, send_reminder_delivery

pytestmark = pytest.mark.django_db


def _due_lesson(parents: int = 1) -> Lesson:
    lesson = LessonFactory(start_time=timezone.now() + datetime.timedelta(hours=23, minutes=50))
    lesson.end_time = lesson.start_time + datetime.timedelta(minutes=30)
    lesson.save()
    for _ in range(parents):
        link_parent_to_student(ParentAccountFactory(), lesson.student)
    return lesson


def test_one_email_per_linked_parent():
    lesson = _due_lesson(parents=2)

    send_lesson_reminders()

    assert ReminderDelivery.objects.filter(lesson=lesson, status="sent").count() == 2
    assert len(mail.outbox) == 2
    lesson.refresh_from_db()
    assert lesson.reminder_sent_at is not None


def test_running_the_sweep_many_times_never_duplicates():
    _due_lesson(parents=2)

    for _ in range(3):
        send_lesson_reminders()
    services.enqueue_due_reminders()  # even directly, after the lesson was swept

    assert ReminderDelivery.objects.count() == 2
    assert len(mail.outbox) == 2


def test_lessons_outside_the_window_or_cancelled_are_ignored():
    far = LessonFactory(start_time=timezone.now() + datetime.timedelta(hours=48))
    link_parent_to_student(ParentAccountFactory(), far.student)
    cancelled = _due_lesson()
    cancel_lesson(cancelled, status=Lesson.Status.CANCELLED)

    send_lesson_reminders()

    assert ReminderDelivery.objects.count() == 0
    assert len(mail.outbox) == 0


def test_lesson_cancelled_after_enqueue_is_skipped():
    lesson = _due_lesson()
    services.enqueue_due_reminders()
    cancel_lesson(lesson, status=Lesson.Status.CANCELLED)

    send_lesson_reminders()

    assert ReminderDelivery.objects.get().status == "skipped"
    assert len(mail.outbox) == 0


def test_transient_send_failure_is_retried_and_sent_once(monkeypatch):
    _due_lesson()
    real_send = services.send_mail
    calls = []

    def flaky_send(**kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise OSError("SMTP temporarily unavailable")
        return real_send(**kwargs)

    monkeypatch.setattr(services, "send_mail", flaky_send)

    send_lesson_reminders()  # eager mode: Celery runs the retry immediately

    delivery = ReminderDelivery.objects.get()
    assert (delivery.status, delivery.attempts) == ("sent", 2)
    assert len(mail.outbox) == 1


def test_permanent_failure_gives_up_after_max_attempts(monkeypatch):
    _due_lesson()

    def always_down(**kwargs):
        raise OSError("SMTP down")

    monkeypatch.setattr(services, "send_mail", always_down)

    send_lesson_reminders()

    delivery = ReminderDelivery.objects.get()
    assert delivery.status == "failed"
    assert delivery.attempts == services.MAX_ATTEMPTS
    assert "SMTP down" in delivery.last_error


def test_delivery_left_by_a_dead_worker_is_picked_up_after_the_lease():
    _due_lesson()
    services.enqueue_due_reminders()
    delivery = ReminderDelivery.objects.get()
    # A worker claimed it and died: status "sending", lease taken 11 minutes ago.
    ReminderDelivery.objects.filter(pk=delivery.pk).update(
        status="sending", claimed_at=timezone.now() - datetime.timedelta(minutes=11)
    )

    send_lesson_reminders()

    delivery.refresh_from_db()
    assert delivery.status == "sent"
    assert len(mail.outbox) == 1


def test_fresh_lease_is_respected():
    _due_lesson()
    services.enqueue_due_reminders()
    delivery = ReminderDelivery.objects.get()
    ReminderDelivery.objects.filter(pk=delivery.pk).update(
        status="sending", claimed_at=timezone.now()
    )

    assert send_reminder_delivery(delivery.pk) == "not-claimable"
    assert len(mail.outbox) == 0


def test_sent_delivery_is_never_sent_again():
    _due_lesson()
    send_lesson_reminders()
    delivery = ReminderDelivery.objects.get()

    assert send_reminder_delivery(delivery.pk) == "not-claimable"
    assert len(mail.outbox) == 1


def test_enqueue_cost_does_not_grow_with_parents(django_assert_num_queries):
    for _ in range(5):
        _due_lesson(parents=3)

    # 3 reads (lessons, students, parent links), then per lesson: SAVEPOINT, claim UPDATE,
    # one bulk INSERT for all its parents, RELEASE (inside tests atomic() is a savepoint).
    with django_assert_num_queries(3 + 5 * 4):
        assert services.enqueue_due_reminders() == 5
    assert ReminderDelivery.objects.count() == 15
