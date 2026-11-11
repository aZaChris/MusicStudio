"""Clear the sign-in lock of one account (operator action, audited)."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.audit import services as audit

from ...models import User


class Command(BaseCommand):
    help = "Unlock an account locked after too many wrong passwords."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("email")

    def handle(self, *args: Any, **options: Any) -> None:
        user = User.objects.filter(email__iexact=options["email"].strip()).first()
        if user is None:
            raise CommandError("No such account.")
        user.failed_logins = 0
        user.lock_level = 0
        user.locked_until = None
        user.save(update_fields=["failed_logins", "lock_level", "locked_until"])
        audit.record(audit.Action.ACCOUNT_UNLOCK_BY_OPERATOR, target=user)
        self.stdout.write(f"Unlocked user #{user.pk}.")
