"""A studio has at most 10 teachers (FR-011)."""

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from apps.common.factories import StudentFactory, StudioFactory, TeacherFactory, UserFactory
from apps.studios.models import Teacher
from apps.studios.services import add_teacher_to_studio, create_solo_teacher

pytestmark = pytest.mark.django_db


def test_eleventh_teacher_is_refused():
    studio = StudioFactory()
    for _ in range(10):
        add_teacher_to_studio(TeacherFactory(), studio)

    with pytest.raises(ValidationError):
        add_teacher_to_studio(TeacherFactory(), studio)

    assert Teacher.objects.filter(studio=studio).count() == 10


@override_settings(STUDIO_MAX_TEACHERS=2)
def test_admin_validation_uses_the_same_rule():
    studio = StudioFactory()
    TeacherFactory.create_batch(2, studio=studio)
    newcomer = Teacher(user=UserFactory(), studio=studio)

    with pytest.raises(ValidationError):
        newcomer.full_clean()


def test_teacher_with_students_cannot_change_studio():
    student = StudentFactory()

    with pytest.raises(ValidationError):
        add_teacher_to_studio(student.teacher, StudioFactory())


def test_solo_teacher_owns_a_personal_studio():
    teacher = create_solo_teacher(UserFactory(email="solo@example.com"))

    assert teacher.is_owner
    assert teacher.studio.name == "solo@example.com"
    assert teacher.studio.owner == teacher
