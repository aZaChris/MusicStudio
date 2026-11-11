"""A small world for object-level authorization (IDOR) tests.

Two studios. Studio A has an owner, two teachers, a minor with a parent and an adult student
with their own account. Studio B has an owner, a teacher and a minor with a parent. Every
student has one lesson, one package and one payment, so every endpoint has a target.
"""

import datetime
from dataclasses import dataclass, field

from apps.accounts.models import User
from apps.common.factories import (
    LessonFactory,
    PackageFactory,
    ParentAccountFactory,
    StudentFactory,
    TeacherFactory,
    link_parent_to_student,
    make_student_account,
)
from apps.common.tests.helpers import make_studio_owner
from apps.lessons.models import Lesson
from apps.packages.models import Package
from apps.payments.models import Payment
from apps.students.models import Student


@dataclass
class Holdings:
    """One student and the objects hanging off it."""

    student: Student
    lesson: Lesson
    package: Package
    payment: Payment

    def ids(self) -> dict[str, int]:
        return {
            "student": self.student.pk,
            "lesson": self.lesson.pk,
            "package": self.package.pk,
            "payment": self.payment.pk,
        }


def _holdings(teacher) -> Holdings:  # type: ignore[no-untyped-def]
    student = StudentFactory(teacher=teacher)
    package = PackageFactory(student=student)
    return Holdings(
        student=student,
        lesson=LessonFactory(student=student, notes="private note"),
        package=package,
        payment=Payment.objects.create(
            student=student,
            package=package,
            amount="50.00",
            date=datetime.date.today(),
            method=Payment.Method.CASH,
        ),
    )


@dataclass
class World:
    users: dict[str, User] = field(default_factory=dict)
    # who → the holdings that user legitimately sees
    a1: Holdings | None = None  # studio A, teacher A1, minor with parent A
    a2: Holdings | None = None  # studio A, teacher A2, adult student with own account
    b1: Holdings | None = None  # studio B, teacher B1, minor with parent B


def build_world() -> World:
    world = World()
    owner_a = make_studio_owner()
    teacher_a1 = TeacherFactory(studio=owner_a.studio)
    teacher_a2 = TeacherFactory(studio=owner_a.studio)
    owner_b = make_studio_owner()
    teacher_b1 = TeacherFactory(studio=owner_b.studio)

    world.a1 = _holdings(teacher_a1)
    world.a2 = _holdings(teacher_a2)
    world.b1 = _holdings(teacher_b1)

    parent_a = ParentAccountFactory()
    link_parent_to_student(parent_a, world.a1.student)
    parent_b = ParentAccountFactory()
    link_parent_to_student(parent_b, world.b1.student)

    world.users = {
        "owner_a": owner_a.user,
        "teacher_a1": teacher_a1.user,
        "teacher_a2": teacher_a2.user,
        "owner_b": owner_b.user,
        "teacher_b1": teacher_b1.user,
        "parent_a": parent_a.user,
        "parent_b": parent_b.user,
        "student_a2": make_student_account(world.a2.student),
    }
    return world
