import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.lessons.models import Lesson
from apps.packages.models import Package
from apps.payments.models import Payment
from apps.students.models import ParentAccount, ParentStudentLink, Student
from apps.studios.models import Studio, Teacher


class Command(BaseCommand):
    help = (
        "Seed a demo scenario for local/manual validation "
        "(see specs/001-musicstudio-mvp/quickstart.md)"
    )

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data…")

        # Solo teacher
        solo_user = self._get_or_create_user("solo.teacher@example.com", User.Role.TEACHER)
        solo_teacher, _ = Teacher.objects.get_or_create(user=solo_user, defaults={"studio": None})

        # Studio owner + 2 teachers
        studio, _ = Studio.objects.get_or_create(name="Studio di Musica Bianchi")
        owner_user = self._get_or_create_user("owner@example.com", User.Role.STUDIO_OWNER)
        owner_teacher, _ = Teacher.objects.get_or_create(
            user=owner_user, defaults={"studio": studio, "is_owner": True}
        )
        if not studio.owner_id:
            studio.owner = owner_teacher
            studio.save(update_fields=["owner"])

        member_user = self._get_or_create_user("teacher2@example.com", User.Role.TEACHER)
        member_teacher, _ = Teacher.objects.get_or_create(
            user=member_user, defaults={"studio": studio}
        )

        # Students with packages (one low, one normal, one for the solo teacher)
        low_student = self._get_or_create_student("Giulia", "Rossi", "Piano", owner_teacher)
        self._get_or_create_package(low_student, total=8, remaining=1)

        normal_student = self._get_or_create_student("Marco", "Verdi", "Chitarra", member_teacher)
        self._get_or_create_package(normal_student, total=8, remaining=6)

        solo_student = self._get_or_create_student("Sara", "Neri", "Violino", solo_teacher)
        solo_package = self._get_or_create_package(solo_student, total=10, remaining=9)

        # A lesson today (US1 completion demo) and one ~24h out (US4 reminder demo)
        Lesson.objects.get_or_create(
            student=solo_student,
            teacher=solo_teacher,
            start_time=timezone.now().replace(hour=15, minute=0, second=0, microsecond=0),
            defaults={"package": solo_package, "duration_minutes": 45},
        )
        Lesson.objects.get_or_create(
            student=low_student,
            teacher=owner_teacher,
            start_time=timezone.now() + datetime.timedelta(hours=24),
            defaults={"duration_minutes": 30},
        )

        # A pending payment
        Payment.objects.get_or_create(
            student=normal_student,
            amount="120.00",
            date=timezone.localdate(),
            method=Payment.Method.BANK_TRANSFER,
            defaults={"status": Payment.Status.PENDING},
        )

        # A parent linked to the low-package student (US3 demo)
        parent_user = self._get_or_create_user("parent@example.com", User.Role.PARENT)
        parent_account, _ = ParentAccount.objects.get_or_create(user=parent_user)
        ParentStudentLink.objects.get_or_create(parent=parent_account, student=low_student)

        self.stdout.write(self.style.SUCCESS("Done. Demo logins (password: password123):"))
        for email in [
            "solo.teacher@example.com",
            "owner@example.com",
            "teacher2@example.com",
            "parent@example.com",
        ]:
            self.stdout.write(f"  - {email}")

    def _get_or_create_user(self, email: str, role: str) -> User:
        user, created = User.objects.get_or_create(
            email=email, defaults={"username": email, "role": role}
        )
        if created:
            user.set_password("password123")
            user.save()
        return user

    def _get_or_create_student(
        self, first: str, last: str, instrument: str, teacher: Teacher
    ) -> Student:
        student, _ = Student.objects.get_or_create(
            first_name=first, last_name=last, teacher=teacher, defaults={"instrument": instrument}
        )
        return student

    def _get_or_create_package(self, student: Student, total: int, remaining: int) -> Package:
        package, _ = Package.objects.get_or_create(
            student=student,
            defaults={
                "total_lessons": total,
                "lessons_remaining": remaining,
                "purchase_date": timezone.localdate(),
                "price": "150.00",
            },
        )
        return package
