"""Audit G5: a malformed ?week= must be a 400, never a 500."""

import datetime

import pytest
from django.utils import timezone

from apps.common.factories import LessonFactory, StudentFactory
from apps.common.tests.helpers import client_for

pytestmark = pytest.mark.django_db


def test_invalid_week_returns_400():
    student = StudentFactory()

    res = client_for(student.teacher.user).get("/api/v1/lessons/?week=garbage")

    assert res.status_code == 400
    assert "week" in res.data


def test_week_param_selects_that_week_only():
    student = StudentFactory()
    in_week = LessonFactory(
        student=student,
        start_time=timezone.make_aware(datetime.datetime(2026, 3, 4, 10, 0)),  # Wednesday
    )
    LessonFactory(
        student=student,
        start_time=timezone.make_aware(datetime.datetime(2026, 3, 9, 10, 0)),  # next Monday
    )

    res = client_for(student.teacher.user).get("/api/v1/lessons/?week=2026-03-06")

    assert [lesson["id"] for lesson in res.data["results"]] == [in_week.id]


def test_upcoming_and_student_lessons_endpoints():
    student = StudentFactory()
    LessonFactory(student=student)
    client = client_for(student.teacher.user)

    upcoming = client.get("/api/v1/lessons/upcoming/")
    history = client.get(f"/api/v1/students/{student.id}/lessons/")

    assert upcoming.status_code == 200
    assert len(upcoming.data) == 1
    assert history.status_code == 200
    assert len(history.data) == 1
