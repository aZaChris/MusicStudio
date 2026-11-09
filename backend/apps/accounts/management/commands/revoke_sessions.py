from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.accounts.models import User
from apps.accounts.services import revoke_all_sessions


class Command(BaseCommand):
    help = "Revoke every session (refresh token) of one account, e.g. after a stolen device."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("email")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            user = User.objects.get(email__iexact=options["email"])
        except User.DoesNotExist as exc:
            raise CommandError("No account with that email.") from exc
        count = revoke_all_sessions(user)
        self.stdout.write(f"Revoked {count} session(s). Access tokens expire within minutes.")
