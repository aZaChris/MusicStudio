"""Shared test factories — used across apps' test suites, not itself a test module."""

import datetime

import factory

from apps.accounts.models import User
from apps.lessons.models import Lesson
from apps.packages.models import Package
from apps.students.models import ParentAccount, ParentStudentLink, Student
from apps.studios.models import Studio, Teacher


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    role = User.Role.TEACHER

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


class LessonFactory(factory.django.DjangoModelFactory[Lesson]):
    class Meta:
        model = Lesson

    student = factory.SubFactory(StudentFactory)
    teacher = factory.LazyAttribute(lambda o: o.student.teacher)
    package = None
    start_time = factory.LazyFunction(
        lambda: datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
    )


class ParentAccountFactory(factory.django.DjangoModelFactory[ParentAccount]):
    class Meta:
        model = ParentAccount

    user = factory.SubFactory(UserFactory, role=User.Role.PARENT)


def link_parent_to_student(parent: ParentAccount, student: Student) -> ParentStudentLink:
    return ParentStudentLink.objects.create(parent=parent, student=student)
