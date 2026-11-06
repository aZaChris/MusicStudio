"""No overlapping active lessons per teacher or per student (ADR-009)."""

import datetime

import pytest
from django.db import IntegrityError, OperationalError
from django.utils import timezone
from psycopg.errors import DeadlockDetected

from apps.common.factories import StudentFactory, TeacherFactory
from apps.common.tests.helpers import client_for
from apps.lessons.models import Lesson
from apps.lessons.services import _guarded_write, cancel_lesson
from apps.students.services import reassign_student

pytestmark = pytest.mark.django_db

TEN = timezone.make_aware(datetime.datetime(2026, 12, 1, 10, 0))


def _iso(dt: datetime.datetime) -> str:
    return dt.isoformat()


def _book(client, student, start, minutes=30):
    return client.post(
        "/api/v1/lessons/",
        {"student": student.id, "start_time": _iso(start), "duration_minutes": minutes},
    )


def test_overlap_same_teacher_returns_409():
    student = StudentFactory()
    other_student = StudentFactory(teacher=student.teacher)
    client = client_for(student.teacher.user)
    assert _book(client, student, TEN, 45).status_code == 201

    res = _book(client, other_student, TEN + datetime.timedelta(minutes=30))

    assert res.status_code == 409
    assert res.data["code"] == "lesson_overlap"
    assert "teacher" in res.data["detail"]
    assert Lesson.objects.count() == 1


def test_overlap_same_student_with_another_teacher_returns_409():
    """Realistic path: the student moves to another teacher but keeps an old lesson."""
    student = StudentFactory()
    old_client = client_for(student.teacher.user)
    assert _book(old_client, student, TEN, 45).status_code == 201
    new_teacher = TeacherFactory(studio=student.studio)
    reassign_student(student, new_teacher)

    res = _book(client_for(new_teacher.user), student, TEN + datetime.timedelta(minutes=15))

    assert res.status_code == 409
    assert "student" in res.data["detail"]


def test_back_to_back_lessons_are_allowed():
    student = StudentFactory()
    client = client_for(student.teacher.user)

    first = _book(client, student, TEN, 45)
    second = _book(client, student, TEN + datetime.timedelta(minutes=45), 30)

    assert (first.status_code, second.status_code) == (201, 201)
    end = datetime.datetime.fromisoformat(second.data["end_time"])
    assert end == TEN + datetime.timedelta(minutes=75)
    assert second.data["duration_minutes"] == 30


def test_cancelled_lesson_frees_the_slot():
    student = StudentFactory()
    client = client_for(student.teacher.user)
    first = Lesson.objects.get(pk=_book(client, student, TEN, 45).data["id"])
    cancel_lesson(first, status=Lesson.Status.CANCELLED)

    assert _book(client, student, TEN, 45).status_code == 201


def test_moving_a_lesson_onto_an_occupied_slot_returns_409():
    student = StudentFactory()
    client = client_for(student.teacher.user)
    _book(client, student, TEN, 45)
    later = _book(client, student, TEN + datetime.timedelta(hours=2), 30).data["id"]

    res = client.patch(f"/api/v1/lessons/{later}/", {"start_time": _iso(TEN)})

    assert res.status_code == 409
    assert Lesson.objects.get(pk=later).start_time == TEN + datetime.timedelta(hours=2)


def test_changing_duration_recomputes_end_time():
    student = StudentFactory()
    client = client_for(student.teacher.user)
    lesson_id = _book(client, student, TEN, 30).data["id"]

    res = client.patch(f"/api/v1/lessons/{lesson_id}/", {"duration_minutes": 60})

    assert res.status_code == 200
    assert Lesson.objects.get(pk=lesson_id).end_time == TEN + datetime.timedelta(hours=1)


def test_completing_a_cancelled_lesson_whose_slot_was_taken_returns_409():
    student = StudentFactory()
    client = client_for(student.teacher.user)
    first = Lesson.objects.get(pk=_book(client, student, TEN, 45).data["id"])
    cancel_lesson(first, status=Lesson.Status.CANCELLED)
    _book(client, student, TEN, 45)

    res = client.post(f"/api/v1/lessons/{first.id}/complete/", {})

    assert res.status_code == 409
    first.refresh_from_db()
    assert first.status == Lesson.Status.CANCELLED


def test_overlap_uses_real_time_across_daylight_saving_change():
    """2026-10-25 03:00 CEST → 02:00 CET: the hour 02:00-03:00 happens twice in Rome.

    A lesson 00:30-01:30 UTC and one 01:00-02:00 UTC are both "02:xx" on the wall clock but
    really overlap by 30 minutes; one starting 01:30 UTC does not.
    """
    student = StudentFactory()
    client = client_for(student.teacher.user)
    utc = datetime.UTC
    first = datetime.datetime(2026, 10, 25, 0, 30, tzinfo=utc)

    assert _book(client, student, first, 60).status_code == 201
    assert _book(client, student, first + datetime.timedelta(minutes=30), 60).status_code == 409
    assert _book(client, student, first + datetime.timedelta(minutes=60), 60).status_code == 201


def test_invalid_duration_is_rejected():
    student = StudentFactory()

    res = _book(client_for(student.teacher.user), student, TEN, 0)

    assert res.status_code == 400
    assert "duration_minutes" in res.data


def _deadlock() -> OperationalError:
    try:
        raise OperationalError("deadlock detected") from DeadlockDetected("40P01")
    except OperationalError as exc:
        return exc


def test_guarded_write_retries_after_a_deadlock():
    calls = []

    def write():
        calls.append(1)
        if len(calls) == 1:
            raise _deadlock()
        return "ok"

    assert _guarded_write(write) == "ok"
    assert len(calls) == 2


def test_guarded_write_gives_up_after_repeated_deadlocks():
    def write():
        raise _deadlock()

    with pytest.raises(OperationalError):
        _guarded_write(write)


def test_guarded_write_reraises_unrelated_integrity_errors():
    def write():
        raise IntegrityError("some other constraint")

    with pytest.raises(IntegrityError):
        _guarded_write(write)
