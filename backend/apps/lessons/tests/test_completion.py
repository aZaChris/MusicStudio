import pytest

from apps.common.factories import LessonFactory, PackageFactory, StudentFactory
from apps.lessons.models import Lesson
from apps.lessons.services import cancel_lesson, complete_lesson

pytestmark = pytest.mark.django_db


def test_complete_lesson_decrements_package_once():
    student = StudentFactory()
    package = PackageFactory(student=student, total_lessons=8, lessons_remaining=8)
    lesson = LessonFactory(student=student, package=package)

    complete_lesson(lesson, note="Great progress")

    lesson.refresh_from_db()
    package.refresh_from_db()
    assert lesson.status == Lesson.Status.COMPLETED
    assert lesson.notes == "Great progress"
    assert package.lessons_remaining == 7


def test_complete_lesson_is_idempotent():
    student = StudentFactory()
    package = PackageFactory(student=student, total_lessons=8, lessons_remaining=8)
    lesson = LessonFactory(student=student, package=package)

    complete_lesson(lesson)
    complete_lesson(lesson)  # retry / double submit
    complete_lesson(lesson)

    package.refresh_from_db()
    assert package.lessons_remaining == 7


def test_complete_lesson_never_goes_negative():
    student = StudentFactory()
    package = PackageFactory(student=student, total_lessons=8, lessons_remaining=0)
    lesson = LessonFactory(student=student, package=package)

    complete_lesson(lesson)

    package.refresh_from_db()
    assert package.lessons_remaining == 0


@pytest.mark.parametrize("target_status", [Lesson.Status.CANCELLED, Lesson.Status.NO_SHOW])
def test_cancel_does_not_decrement_package(target_status):
    student = StudentFactory()
    package = PackageFactory(student=student, total_lessons=8, lessons_remaining=8)
    lesson = LessonFactory(student=student, package=package)

    cancel_lesson(lesson, status=target_status)

    lesson.refresh_from_db()
    package.refresh_from_db()
    assert lesson.status == target_status
    assert package.lessons_remaining == 8


def test_completed_lesson_with_no_package_does_not_error():
    lesson = LessonFactory(package=None)

    complete_lesson(lesson)

    lesson.refresh_from_db()
    assert lesson.status == Lesson.Status.COMPLETED
