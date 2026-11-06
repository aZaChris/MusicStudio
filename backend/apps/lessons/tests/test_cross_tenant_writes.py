"""Audit G1: a teacher must not write lessons onto another tenant's student/package."""

import pytest

from apps.common.factories import LessonFactory, PackageFactory, StudentFactory, TeacherFactory
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.lessons.models import Lesson

pytestmark = pytest.mark.django_db

START = "2026-12-01T10:00:00Z"


def test_cross_tenant_lesson_create_is_rejected():
    victim_student = StudentFactory()
    attacker = TeacherFactory()

    res = client_for(attacker.user).post(
        "/api/v1/lessons/", {"student": victim_student.id, "start_time": START}
    )

    assert res.status_code == 400
    assert "student" in res.data
    assert not Lesson.objects.filter(student=victim_student).exists()


def test_cross_tenant_lesson_reassign_student_is_rejected():
    own_lesson = LessonFactory()
    victim_student = StudentFactory()

    res = client_for(own_lesson.teacher.user).patch(
        f"/api/v1/lessons/{own_lesson.id}/", {"student": victim_student.id}
    )

    assert res.status_code == 400
    own_lesson.refresh_from_db()
    assert own_lesson.student_id != victim_student.id


def test_cross_tenant_lesson_with_foreign_package_is_rejected():
    own_student = StudentFactory()
    foreign_package = PackageFactory()

    res = client_for(own_student.teacher.user).post(
        "/api/v1/lessons/",
        {"student": own_student.id, "package": foreign_package.id, "start_time": START},
    )

    assert res.status_code == 400
    assert "package" in res.data


def test_lesson_with_package_of_another_own_student_is_rejected():
    student = StudentFactory()
    sibling = StudentFactory(teacher=student.teacher)
    sibling_package = PackageFactory(student=sibling)

    res = client_for(student.teacher.user).post(
        "/api/v1/lessons/",
        {"student": student.id, "package": sibling_package.id, "start_time": START},
    )

    assert res.status_code == 400
    assert "package" in res.data


def test_lesson_create_defaults_teacher_and_active_package():
    student = StudentFactory()
    package = PackageFactory(student=student)

    res = client_for(student.teacher.user).post(
        "/api/v1/lessons/", {"student": student.id, "start_time": START}
    )

    assert res.status_code == 201
    assert res.data["teacher"] == student.teacher.id
    assert res.data["package"] == package.id


def test_lesson_update_to_another_own_student_moves_teacher():
    owner = make_studio_owner()
    from apps.common.factories import TeacherFactory as TF

    member = TF(studio=owner.studio)
    lesson = LessonFactory(student=StudentFactory(teacher=owner))
    other_student = StudentFactory(teacher=member)

    res = client_for(owner.user).patch(
        f"/api/v1/lessons/{lesson.id}/", {"student": other_student.id}
    )

    assert res.status_code == 200
    lesson.refresh_from_db()
    assert lesson.teacher_id == member.id


def test_studio_owner_can_write_for_studio_students_only():
    owner = make_studio_owner()
    member = TeacherFactory(studio=owner.studio)
    studio_student = StudentFactory(teacher=member)
    outside_student = StudentFactory()
    client = client_for(owner.user)

    ok = client.post("/api/v1/lessons/", {"student": studio_student.id, "start_time": START})
    ko = client.post("/api/v1/lessons/", {"student": outside_student.id, "start_time": START})

    assert ok.status_code == 201
    assert ko.status_code == 400
