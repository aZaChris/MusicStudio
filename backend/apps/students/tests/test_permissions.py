import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.factories import StudentFactory, StudioFactory, TeacherFactory

pytestmark = pytest.mark.django_db


def _client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_teacher_only_sees_own_students():
    teacher = TeacherFactory()
    own_student = StudentFactory(teacher=teacher)
    StudentFactory()  # another teacher's student

    client = _client_for(teacher.user)
    res = client.get("/api/v1/students/")

    ids = [s["id"] for s in res.data["results"]]
    assert ids == [own_student.id]


def test_studio_owner_sees_all_students_in_studio():
    studio = StudioFactory()
    owner = TeacherFactory(studio=studio, is_owner=True)
    owner.user.role = User.Role.STUDIO_OWNER
    owner.user.save()
    member = TeacherFactory(studio=studio)
    student_a = StudentFactory(teacher=owner)
    student_b = StudentFactory(teacher=member)
    StudentFactory()  # unrelated studio

    client = _client_for(owner.user)
    res = client.get("/api/v1/students/")

    ids = {s["id"] for s in res.data["results"]}
    assert ids == {student_a.id, student_b.id}


def test_teacher_cannot_retrieve_another_teachers_student():
    outsider = TeacherFactory()
    other_student = StudentFactory()

    client = _client_for(outsider.user)
    res = client.get(f"/api/v1/students/{other_student.id}/")

    assert res.status_code == 404
