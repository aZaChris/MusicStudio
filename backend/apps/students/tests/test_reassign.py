"""Studio owners reassign students within their studio (FR-010)."""

import pytest

from apps.common.factories import (
    LessonFactory,
    ParentAccountFactory,
    StudentFactory,
    TeacherFactory,
    link_parent_to_student,
)
from apps.common.tests.helpers import client_for, make_studio_owner

pytestmark = pytest.mark.django_db


def _reassign(user, student, teacher):
    return client_for(user).post(
        f"/api/v1/students/{student.id}/reassign/", {"teacher": teacher.id}
    )


def test_owner_reassigns_student_within_studio_and_lessons_keep_their_teacher():
    owner = make_studio_owner()
    old_teacher = TeacherFactory(studio=owner.studio)
    new_teacher = TeacherFactory(studio=owner.studio)
    student = StudentFactory(teacher=old_teacher)
    lesson = LessonFactory(student=student)

    res = _reassign(owner.user, student, new_teacher)

    assert res.status_code == 200
    assert res.data["teacher"] == new_teacher.id
    lesson.refresh_from_db()
    assert lesson.teacher_id == old_teacher.id


def test_owner_cannot_reassign_to_a_teacher_of_another_studio():
    owner = make_studio_owner()
    student = StudentFactory(teacher=TeacherFactory(studio=owner.studio))

    res = _reassign(owner.user, student, TeacherFactory())

    assert res.status_code == 400
    assert "teacher" in res.data
    student.refresh_from_db()
    assert student.teacher.studio_id == owner.studio_id


def test_owner_cannot_reassign_a_student_of_another_studio():
    owner = make_studio_owner()
    foreign = StudentFactory()

    assert _reassign(owner.user, foreign, owner).status_code == 404


@pytest.mark.parametrize("who", ["teacher", "parent"])
def test_other_roles_cannot_reassign(who):
    student = StudentFactory()
    if who == "teacher":
        user = student.teacher.user
    else:
        parent = ParentAccountFactory()
        link_parent_to_student(parent, student)
        user = parent.user

    res = _reassign(user, student, TeacherFactory(studio=student.studio))

    assert res.status_code == 403


def test_reassign_service_refuses_cross_studio_even_if_called_directly():
    from django.core.exceptions import ValidationError

    from apps.students.services import reassign_student

    with pytest.raises(ValidationError):
        reassign_student(StudentFactory(), TeacherFactory())
