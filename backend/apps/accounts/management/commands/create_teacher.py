from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.accounts.models import User
from apps.studios.services import create_solo_teacher

from ._passwords import ENV_VAR, read_password


class Command(BaseCommand):
    help = (
        "Create a real teacher account with a studio of their own. With --studio-name the "
        "account is the owner of a named studio; without it, a teacher working alone. "
        f"The password is asked on the terminal, or read from ${ENV_VAR}."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--email", required=True)
        parser.add_argument("--studio-name", default=None)

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        email = options["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            # Never touch the password of an account that exists.
            raise CommandError(f"{email} already exists.")
        studio_name = options["studio_name"]
        role = User.Role.STUDIO_OWNER if studio_name else User.Role.TEACHER
        user = User(email=email, username=email, role=role, email_verified=True)
        user.set_password(read_password(email))
        user.save()
        teacher = create_solo_teacher(user, studio_name=studio_name)
        self.stdout.write(
            self.style.SUCCESS(f"Created {role} {email} with studio “{teacher.studio.name}”.")
        )
