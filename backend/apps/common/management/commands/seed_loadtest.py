"""Realistic volume for load tests and restore drills (ADR-022).

Default: 10 studios x 5 teachers x 30 students, one parent per student, one package and
one payment per student, one weekly lesson per student for 40 weeks back and 12 ahead
(~78,000 lessons). Bulk inserts, one password hash reused: seconds, not minutes.

Logins (password `loadtest-password`): owners `lt-owner-<s>@example.com`, teachers
`lt-teacher-<s>-<t>@example.com`, parents `lt-parent-<n>@example.com`.
"""

import datetime
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.lessons.models import Lesson
from apps.packages.models import Package
from apps.payments.models import Payment
from apps.students.models import ParentAccount, ParentStudentLink, Student
from apps.studios.models import Studio, Teacher

PASSWORD = "loadtest-password"  # noqa: S105 - throwaway accounts, refused in production
INSTRUMENTS = ["Piano", "Chitarra", "Violino", "Canto", "Batteria", "Flauto"]


class Command(BaseCommand):
    help = "Create a large synthetic dataset for load tests and restore drills."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--studios", type=int, default=10)
        parser.add_argument("--teachers", type=int, default=5, help="per studio")
        parser.add_argument("--students", type=int, default=30, help="per teacher")
        parser.add_argument("--weeks-back", type=int, default=40)
        parser.add_argument("--weeks-ahead", type=int, default=12)
        parser.add_argument(
            "--i-know-this-is-not-production",
            action="store_true",
            dest="force",
            help="Allow DEBUG=False (prod-like local settings for the load test).",
        )

    def handle(self, *args: Any, **o: Any) -> None:
        if not settings.DEBUG and not o["force"]:
            raise CommandError(
                "seed_loadtest creates thousands of accounts with a known password. "
                "Refusing with DEBUG=False; pass --i-know-this-is-not-production."
            )
        if User.objects.filter(email__startswith="lt-").exists():
            raise CommandError("Load-test data already present (users lt-*). Use a fresh DB.")
        with transaction.atomic():
            counts = self._seed(o)
        self.stdout.write(self.style.SUCCESS(f"Seeded: {counts}"))

    def _seed(self, o: dict[str, Any]) -> dict[str, int]:
        hashed = make_password(PASSWORD)
        today = timezone.localdate()
        # Monday 00:00 of the current week, in the project timezone.
        monday = timezone.make_aware(
            datetime.datetime.combine(
                today - datetime.timedelta(days=today.weekday()), datetime.time()
            )
        )

        studios = Studio.objects.bulk_create(
            [Studio(name=f"Load Studio {s}") for s in range(o["studios"])]
        )
        users, teacher_specs = [], []
        for s, studio in enumerate(studios):
            for t in range(o["teachers"]):
                owner = t == 0
                email = f"lt-owner-{s}@example.com" if owner else f"lt-teacher-{s}-{t}@example.com"
                role = User.Role.STUDIO_OWNER if owner else User.Role.TEACHER
                users.append(User(email=email, username=email, role=role, password=hashed))
                teacher_specs.append((studio, owner))
        users = User.objects.bulk_create(users)
        teachers = Teacher.objects.bulk_create(
            [
                Teacher(user=u, studio=studio, is_owner=owner)
                for u, (studio, owner) in zip(users, teacher_specs, strict=True)
            ]
        )
        for studio, teacher in zip(studios, teachers[:: o["teachers"]], strict=True):
            studio.owner = teacher
        Studio.objects.bulk_update(studios, ["owner"])

        students = Student.objects.bulk_create(
            [
                Student(
                    first_name=f"S{t.pk}-{i}",
                    last_name="Load",
                    instrument=INSTRUMENTS[i % len(INSTRUMENTS)],
                    teacher=t,
                    studio_id=t.studio_id,
                )
                for t in teachers
                for i in range(o["students"])
            ]
        )
        parents_users = User.objects.bulk_create(
            [
                User(
                    email=f"lt-parent-{n}@example.com",
                    username=f"lt-parent-{n}@example.com",
                    role=User.Role.PARENT,
                    password=hashed,
                )
                for n in range(len(students))
            ]
        )
        parents = ParentAccount.objects.bulk_create([ParentAccount(user=u) for u in parents_users])
        ParentStudentLink.objects.bulk_create(
            [ParentStudentLink(parent=p, student=s) for p, s in zip(parents, students, strict=True)]
        )
        packages = Package.objects.bulk_create(
            [
                Package(
                    student=s,
                    total_lessons=10,
                    lessons_remaining=i % 11,
                    purchase_date=today - datetime.timedelta(days=i % 90),
                    price="150.00",
                )
                for i, s in enumerate(students)
            ]
        )
        Payment.objects.bulk_create(
            [
                Payment(
                    student=p.student,
                    package=p,
                    amount=p.price,
                    date=p.purchase_date,
                    method=Payment.Method.BANK_TRANSFER,
                    status=Payment.Status.PAID if i % 4 else Payment.Status.PENDING,
                )
                for i, p in enumerate(packages)
            ]
        )

        # One weekly 45-minute slot per student: weekday i % 5, hour 9 + i // 5.
        # Distinct per teacher, and each student has one teacher: no overlaps (ADR-009).
        now = timezone.now()
        lessons = []
        for i, (student, package) in enumerate(zip(students, packages, strict=True)):
            slot = i % o["students"]
            offset = datetime.timedelta(days=slot % 5, hours=9 + slot // 5)
            for week in range(-o["weeks_back"], o["weeks_ahead"]):
                start = monday + datetime.timedelta(weeks=week) + offset
                past = start < now
                lessons.append(
                    Lesson(
                        student=student,
                        teacher_id=student.teacher_id,
                        package=package,
                        start_time=start,
                        end_time=start + datetime.timedelta(minutes=45),
                        status=Lesson.Status.COMPLETED if past else Lesson.Status.SCHEDULED,
                    )
                )
        Lesson.objects.bulk_create(lessons, batch_size=5000)

        return {
            "studios": len(studios),
            "teachers": len(teachers),
            "students": len(students),
            "parents": len(parents),
            "lessons": len(lessons),
        }
