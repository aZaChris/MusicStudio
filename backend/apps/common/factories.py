"""Shared test factories — used across apps' test suites, not itself a test module."""

import datetime

import factory
from django.utils import timezone

from apps.accounts.models import User
from apps.lessons.models import Lesson
from apps.lessons.selectors import week_bounds
from apps.packages.models import Package
from apps.students.models import ParentAccount, ParentStudentLink, Student
from apps.studios.models import Studio, Teacher


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    role = User.Role.TEACHER
    email_verified = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "password123")
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user


class StudioFactory(factory.django.DjangoModelFactory[Studio]):
    class Meta:
        model = Studio

    name = factory.Sequence(lambda n: f"Studio {n}")


class TeacherFactory(factory.django.DjangoModelFactory[Teacher]):
    class Meta:
        model = Teacher

    user = factory.SubFactory(UserFactory, role=User.Role.TEACHER)
    studio = factory.SubFactory(StudioFactory)  # every teacher belongs to a studio (ADR-010)
    is_owner = False


class StudentFactory(factory.django.DjangoModelFactory[Student]):
    class Meta:
        model = Student

    first_name = factory.Sequence(lambda n: f"Student{n}")
    last_name = "Test"
    instrument = "Piano"
    teacher = factory.SubFactory(TeacherFactory)
    studio = factory.LazyAttribute(lambda o: o.teacher.studio)


class PackageFactory(factory.django.DjangoModelFactory[Package]):
    class Meta:
        model = Package

    student = factory.SubFactory(StudentFactory)
    total_lessons = 8
    lessons_remaining = 8
    purchase_date = factory.LazyFunction(datetime.date.today)
    price = "120.00"


def _factory_start(n: int) -> datetime.datetime:
    """Start time of the n-th factory lesson: 31 minutes apart, cycling within ~20h.

    The spacing keeps lessons of the same teacher or student from tripping the overlap
    constraints. The lesson list shows the current week by default, so a start that would
    fall past the end of the week (Sunday evening, Europe/Rome) moves back one week:
    otherwise the list would be empty and the tests would fail only on Sunday nights.
    """
    now = datetime.datetime.now(datetime.UTC)
    start = now + datetime.timedelta(hours=1, minutes=31 * (n % 40))
    _, week_end = week_bounds(timezone.localdate())
    return start - datetime.timedelta(days=7) if start >= week_end else start


class LessonFactory(factory.django.DjangoModelFactory[Lesson]):
    class Meta:
        model = Lesson

    student = factory.SubFactory(StudentFactory)
    teacher = factory.LazyAttribute(lambda o: o.student.teacher)
    package = None
    start_time = factory.Sequence(_factory_start)
    end_time = factory.LazyAttribute(lambda o: o.start_time + datetime.timedelta(minutes=30))


class ParentAccountFactory(factory.django.DjangoModelFactory[ParentAccount]):
    class Meta:
        model = ParentAccount

    user = factory.SubFactory(UserFactory, role=User.Role.PARENT)


def link_parent_to_student(parent: ParentAccount, student: Student) -> ParentStudentLink:
    return ParentStudentLink.objects.create(parent=parent, student=student)


def make_student_account(student: Student) -> User:
    """Give an adult student their own read-only account (phase 7)."""
    user = UserFactory(role=User.Role.STUDENT)
    student.is_adult = True
    student.user = user
    student.save(update_fields=["is_adult", "user"])
    return user
