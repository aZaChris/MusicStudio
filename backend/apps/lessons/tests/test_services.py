import pytest
from django.core.exceptions import ValidationError

from apps.common.factories import LessonFactory, PackageFactory
from apps.common.tests.helpers import client_for
from apps.lessons.models import Lesson
from apps.lessons.services import cancel_lesson, complete_lesson

pytestmark = pytest.mark.django_db


def test_cancel_rejects_unknown_status():
    lesson = LessonFactory()

    with pytest.raises(ValidationError):
        cancel_lesson(lesson, status="completed")


def test_completed_lesson_cannot_be_cancelled():
    package = PackageFactory()
    lesson = LessonFactory(student=package.student, package=package)
    complete_lesson(lesson)
    lesson.refresh_from_db()

    cancel_lesson(lesson, status=Lesson.Status.CANCELLED)

    lesson.refresh_from_db()
    assert lesson.status == Lesson.Status.COMPLETED


def test_complete_with_stale_instance_does_not_double_decrement():
    """Two requests holding the same in-memory lesson: only the first one decrements."""
    package = PackageFactory(total_lessons=8, lessons_remaining=8)
    lesson = LessonFactory(student=package.student, package=package)
    stale_copy = Lesson.objects.get(pk=lesson.pk)

    complete_lesson(lesson)
    complete_lesson(stale_copy)  # still says "scheduled" in memory

    package.refresh_from_db()
    assert package.lessons_remaining == 7


def test_cancel_endpoint():
    lesson = LessonFactory()

    res = client_for(lesson.teacher.user).post(
        f"/api/v1/lessons/{lesson.id}/cancel/", {"status": "no_show"}
    )

    assert res.status_code == 200
    assert res.data["status"] == "no_show"
