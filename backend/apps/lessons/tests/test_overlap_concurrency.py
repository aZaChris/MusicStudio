"""Two simultaneous bookings of the same slot: exactly one wins (FR-002, SC-001).

Real concurrency: two threads, each with its own database connection and transaction,
released at the same moment by a barrier. An application-level "check then insert" would
let both pass; the exclusion constraint makes the second one wait for the first and fail.
"""

import datetime
import threading

import pytest
from django.db import connection
from django.utils import timezone

from apps.common.factories import StudentFactory
from apps.lessons.models import Lesson
from apps.lessons.services import LessonOverlapError, create_lesson
from apps.students.models import Student

START = timezone.make_aware(datetime.datetime(2026, 12, 2, 17, 0))


@pytest.mark.django_db(transaction=True)
def test_concurrent_bookings_for_the_same_slot_only_one_wins():
    student_a = StudentFactory()
    student_b = StudentFactory(teacher=student_a.teacher)  # same teacher, different students
    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def book(student_id: int) -> None:
        try:
            student = Student.objects.select_related("teacher").get(pk=student_id)
            barrier.wait(timeout=5)
            create_lesson(student=student, start_time=START, duration_minutes=45)
            result = "created"
        except LessonOverlapError:
            result = "conflict"
        finally:
            connection.close()  # each thread owns its connection
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=book, args=(s.id,)) for s in (student_a, student_b)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert sorted(outcomes) == ["conflict", "created"]
    assert Lesson.objects.filter(teacher=student_a.teacher).count() == 1
