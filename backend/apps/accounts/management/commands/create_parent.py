from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.accounts.models import User
from apps.students.models import ParentAccount, ParentStudentLink, Student

from ._passwords import ENV_VAR, read_password


class Command(BaseCommand):
    help = (
        "Create a parent account and link it to one or more students (read-only portal), or "
        "link an existing parent to more students. "
        f"The password is asked on the terminal, or read from ${ENV_VAR}."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--email", required=True)
        parser.add_argument(
            "--student-id", type=int, action="append", required=True, dest="student_ids"
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        email = options["email"].strip().lower()
        students = list(Student.objects.filter(pk__in=options["student_ids"]))
        missing = set(options["student_ids"]) - {s.pk for s in students}
        if missing:
            raise CommandError(f"No student with id {sorted(missing)}.")

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(email=email, username=email, role=User.Role.PARENT)
            user.set_password(read_password(email))
            user.save()
            created = True
        elif user.role != User.Role.PARENT:
            raise CommandError(f"{email} exists and is not a parent account.")
        else:
            created = False

        account, _ = ParentAccount.objects.get_or_create(user=user)
        for student in students:
            ParentStudentLink.objects.get_or_create(parent=account, student=student)
        names = ", ".join(s.full_name for s in students)
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} parent {email}, linked to {names}."))
