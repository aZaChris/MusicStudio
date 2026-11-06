"""Query budgets for the main endpoints (Constitution III, audit G2).

Each endpoint is measured with 1 and with 25 rows: the count must be identical (no N+1)
and equal to the pinned budget. If you add a field that needs data from another table,
this test tells you to add a select_related/prefetch/annotation to the selector.
"""

from collections.abc import Callable

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.common.factories import (
    LessonFactory,
    PackageFactory,
    ParentAccountFactory,
    StudentFactory,
    TeacherFactory,
    link_parent_to_student,
)
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.payments.models import Payment
from apps.studios.models import Teacher

pytestmark = pytest.mark.django_db


def _seed_student(teacher: Teacher) -> None:
    student = StudentFactory(teacher=teacher)
    package = PackageFactory(student=student, total_lessons=8, lessons_remaining=1)
    LessonFactory(student=student, package=package)
    Payment.objects.create(student=student, amount="10", date="2026-01-01", method="cash")


def _count(user, url: str) -> int:
    client = client_for(user)  # fresh user per request, as with real token auth
    with CaptureQueriesContext(connection) as ctx:
        res = client.get(url)
    assert res.status_code == 200, res.data
    return len(ctx)


# Budgets for a teacher. With JWT auth add 1 query (loading the user from the token).
# The first query is always request.user.teacher, needed for tenant scoping.
TEACHER_BUDGETS = {
    "/api/v1/students/": 4,  # teacher, count, students+payment subquery, active packages
    "/api/v1/lessons/": 3,  # teacher, count, lessons+student
    "/api/v1/packages/": 3,  # teacher, count, packages
    "/api/v1/payments/": 3,  # teacher, count, payments+student
    "/api/v1/dashboard/": 6,  # teacher, week, upcoming, pending, active, low-package
}


@pytest.mark.parametrize(("url", "budget"), TEACHER_BUDGETS.items())
def test_num_queries_constant_for_teacher(url: str, budget: int):
    teacher = TeacherFactory()

    _seed_student(teacher)
    with_one = _count(teacher.user, url)
    for _ in range(24):
        _seed_student(teacher)
    with_many = _count(teacher.user, url)

    assert with_one == with_many == budget


def test_num_queries_constant_for_studio_teachers():
    owner = make_studio_owner()
    measure: Callable[[], int] = lambda: _count(owner.user, "/api/v1/studio/teachers/")  # noqa: E731

    with_one = measure()
    for _ in range(9):
        TeacherFactory(studio=owner.studio)

    assert with_one == measure() == 3  # teacher, count, teachers+user


def test_num_queries_constant_for_parent_roster():
    parent = ParentAccountFactory()
    teacher = TeacherFactory()

    def add_child() -> None:
        _seed_student(teacher)
        link_parent_to_student(parent, teacher.students.order_by("-id").first())

    add_child()
    with_one = _count(parent.user, "/api/v1/students/")
    for _ in range(4):
        add_child()

    assert with_one == _count(parent.user, "/api/v1/students/") == 4
