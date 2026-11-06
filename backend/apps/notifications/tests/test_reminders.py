import datetime

import pytest
from django.core import mail
from django.utils import timezone

from apps.common.factories import LessonFactory, ParentAccountFactory, link_parent_to_student
from apps.lessons.models import Lesson
from apps.lessons.services import cancel_lesson
from apps.notifications.tasks import send_lesson_reminders

pytestmark = pytest.mark.django_db


def test_sends_reminder_for_lesson_in_24h_window():
    lesson = LessonFactory(start_time=timezone.now() + datetime.timedelta(hours=23, minutes=50))
    parent = ParentAccountFactory()
    link_parent_to_student(parent, lesson.student)

    sent = send_lesson_reminders()

    lesson.refresh_from_db()
    assert sent == 1
    assert lesson.reminder_sent_at is not None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [parent.user.email]


def test_reminder_sweep_is_idempotent():
    lesson = LessonFactory(start_time=timezone.now() + datetime.timedelta(hours=23, minutes=50))
    parent = ParentAccountFactory()
    link_parent_to_student(parent, lesson.student)

    send_lesson_reminders()
    send_lesson_reminders()  # re-run the same window

    assert len(mail.outbox) == 1


def test_skips_lesson_outside_window():
    lesson = LessonFactory(start_time=timezone.now() + datetime.timedelta(hours=48))
    parent = ParentAccountFactory()
    link_parent_to_student(parent, lesson.student)

    sent = send_lesson_reminders()

    lesson.refresh_from_db()
    assert sent == 0
    assert lesson.reminder_sent_at is None
    assert len(mail.outbox) == 0


def test_skips_cancelled_lesson_in_window():
    lesson = LessonFactory(start_time=timezone.now() + datetime.timedelta(hours=23, minutes=50))
    cancel_lesson(lesson, status=Lesson.Status.CANCELLED)
    parent = ParentAccountFactory()
    link_parent_to_student(parent, lesson.student)

    sent = send_lesson_reminders()

    assert sent == 0
    assert len(mail.outbox) == 0


def test_lesson_claimed_by_a_concurrent_sweep_is_not_sent_again(monkeypatch):
    """Overlap: another sweep claims the lesson after we selected it but before we send."""
    from apps.notifications import services

    lesson = LessonFactory(start_time=timezone.now() + datetime.timedelta(hours=23, minutes=50))
    link_parent_to_student(ParentAccountFactory(), lesson.student)
    original_due = services.due_lessons

    def due_then_claimed_elsewhere(now):
        selected = list(original_due(now))  # we already hold the lesson in memory...
        Lesson.objects.filter(pk=lesson.pk).update(reminder_sent_at=now)  # ...others claim it
        return selected

    monkeypatch.setattr(services, "due_lessons", due_then_claimed_elsewhere)

    assert services.send_due_reminders() == 0
    assert len(mail.outbox) == 0


def test_claim_is_won_only_once():
    from apps.notifications.services import claim_lesson

    lesson = LessonFactory()
    now = timezone.now()

    assert claim_lesson(lesson.pk, now) is True
    assert claim_lesson(lesson.pk, now) is False


def test_email_failure_is_logged_and_not_retried(monkeypatch, caplog):
    from apps.notifications import services

    lesson = LessonFactory(start_time=timezone.now() + datetime.timedelta(hours=23, minutes=50))
    link_parent_to_student(ParentAccountFactory(), lesson.student)

    def boom(**kwargs):
        raise OSError("smtp down")

    monkeypatch.setattr(services, "send_mail", boom)

    assert services.send_due_reminders() == 1
    lesson.refresh_from_db()
    assert lesson.reminder_sent_at is not None
    assert "Reminder email failed" in caplog.text


def test_sweep_query_count_is_constant(django_assert_num_queries):
    start = timezone.now() + datetime.timedelta(hours=23, minutes=50)
    for _ in range(5):
        lesson = LessonFactory(start_time=start)
        link_parent_to_student(ParentAccountFactory(), lesson.student)

    # select lessons+students, prefetch links+parents+users, then one claim UPDATE per lesson
    with django_assert_num_queries(2 + 5):
        assert send_lesson_reminders() == 5
