import datetime

import pytest
from django.core import mail
from django.utils import timezone

from apps.common.factories import LessonFactory, ParentAccountFactory, link_parent_to_student
from apps.lessons.models import Lesson
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
    lesson.cancel(Lesson.Status.CANCELLED)
    parent = ParentAccountFactory()
    link_parent_to_student(parent, lesson.student)

    sent = send_lesson_reminders()

    assert sent == 0
    assert len(mail.outbox) == 0
