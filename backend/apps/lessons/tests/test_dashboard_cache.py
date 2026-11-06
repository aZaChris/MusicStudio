"""Dashboard cache with per-studio version invalidation (US5, ADR-017)."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.common.factories import (
    LessonFactory,
    ParentAccountFactory,
    StudentFactory,
    TeacherFactory,
    link_parent_to_student,
)
from apps.common.tests.helpers import client_for
from apps.lessons import cache as dashboard_cache
from apps.lessons.services import complete_lesson

pytestmark = pytest.mark.django_db


def _dashboard(user):
    client = client_for(user)  # loads the user; not part of the request's cost
    with CaptureQueriesContext(connection) as ctx:
        res = client.get("/api/v1/dashboard/")
    assert res.status_code == 200
    return res.data, len(ctx)


def test_second_request_is_served_from_the_cache():
    student = StudentFactory()
    LessonFactory(student=student)

    _, cold = _dashboard(student.teacher.user)
    _, warm = _dashboard(student.teacher.user)

    assert cold == 6
    assert warm == 1  # only the tenant context; no dashboard queries


def test_a_write_in_the_studio_makes_the_next_dashboard_fresh(
    django_capture_on_commit_callbacks,
):
    student = StudentFactory()
    teacher_user = student.teacher.user
    with django_capture_on_commit_callbacks(execute=True):
        _dashboard(teacher_user)
        StudentFactory(teacher=student.teacher)  # new active student → signal → bump

    data, queries = _dashboard(teacher_user)

    assert data["active_students_count"] == 2
    assert queries == 6  # recomputed


def test_completing_a_lesson_invalidates(django_capture_on_commit_callbacks):
    student = StudentFactory()
    lesson = LessonFactory(student=student)
    _dashboard(student.teacher.user)

    with django_capture_on_commit_callbacks(execute=True):
        complete_lesson(lesson)

    _, queries = _dashboard(student.teacher.user)
    assert queries == 6


def test_another_studio_is_not_invalidated(django_capture_on_commit_callbacks):
    mine = StudentFactory()
    _dashboard(mine.teacher.user)

    with django_capture_on_commit_callbacks(execute=True):
        StudentFactory(teacher=TeacherFactory())  # different studio

    _, queries = _dashboard(mine.teacher.user)
    assert queries == 1


def test_parent_dashboard_is_not_cached():
    student = StudentFactory()
    parent = ParentAccountFactory()
    link_parent_to_student(parent, student)

    _, first = _dashboard(parent.user)
    _, second = _dashboard(parent.user)

    assert first == second > 1


def test_cache_outage_falls_back_to_computing(monkeypatch):
    student = StudentFactory()

    def broken(*args, **kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr(dashboard_cache.cache, "get", broken)
    monkeypatch.setattr(dashboard_cache.cache, "add", broken)

    data, _ = _dashboard(student.teacher.user)

    assert data["active_students_count"] == 1


def test_bump_survives_a_missing_version_key():
    dashboard_cache.cache.delete("dashboard:studio-version:999")

    dashboard_cache.bump_studio_version(999)

    assert dashboard_cache.studio_version(999) == 2


def test_redis_outage_does_not_take_the_api_down(monkeypatch):
    """Regression: DRF throttles read counters from the cache; with Redis down every
    request was a 500. Throttles now fail open (apps/common/throttling.py)."""
    from django.core.cache import cache

    student = StudentFactory()

    def broken(*args, **kwargs):
        raise ConnectionError("redis down")

    for method in ("get", "set", "add", "incr"):
        monkeypatch.setattr(cache, method, broken)

    assert client_for(student.teacher.user).get("/api/v1/students/").status_code == 200
