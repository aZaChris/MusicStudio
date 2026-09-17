import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.factories import (
    LessonFactory,
    StudentFactory,
    StudioFactory,
    TeacherFactory,
)

pytestmark = pytest.mark.django_db


def _client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_teacher_cannot_complete_another_teachers_lesson():
    other_lesson = LessonFactory()  # belongs to some other teacher/student
    outsider = TeacherFactory()

    client = _client_for(outsider.user)
    res = client.post(f"/api/v1/lessons/{other_lesson.id}/complete/", {}, format="json")

    assert res.status_code == 404  # scoped out of existence, not merely forbidden
    other_lesson.refresh_from_db()
    assert other_lesson.status == "scheduled"


def test_teacher_can_complete_own_lesson():
    student = StudentFactory()
    lesson = LessonFactory(student=student, teacher=student.teacher)

    client = _client_for(student.teacher.user)
    res = client.post(
        f"/api/v1/lessons/{lesson.id}/complete/", {"note": "Nice work"}, format="json"
    )

    assert res.status_code == 200
    lesson.refresh_from_db()
    assert lesson.status == "completed"


def test_studio_owner_can_complete_any_lesson_in_their_studio():
    studio = StudioFactory()
    owner = TeacherFactory(studio=studio, is_owner=True)
    owner.user.role = User.Role.STUDIO_OWNER
    owner.user.save()
    member = TeacherFactory(studio=studio)
    student = StudentFactory(teacher=member)
    lesson = LessonFactory(student=student, teacher=member)

    client = _client_for(owner.user)
    res = client.post(f"/api/v1/lessons/{lesson.id}/complete/", {}, format="json")

    assert res.status_code == 200


def test_studio_owner_cannot_complete_lesson_outside_their_studio():
    owner = TeacherFactory(studio=StudioFactory(), is_owner=True)
    owner.user.role = User.Role.STUDIO_OWNER
    owner.user.save()
    outside_lesson = LessonFactory()  # different studio entirely

    client = _client_for(owner.user)
    res = client.post(f"/api/v1/lessons/{outside_lesson.id}/complete/", {}, format="json")

    assert res.status_code == 404


def test_unauthenticated_request_is_rejected():
    lesson = LessonFactory()
    client = APIClient()

    res = client.post(f"/api/v1/lessons/{lesson.id}/complete/", {}, format="json")

    assert res.status_code == 401
