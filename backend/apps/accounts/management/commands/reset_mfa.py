"""Remove the second factor of one account (operator action, audited).

For a person who lost both the phone and the recovery codes. Check who they are first:
this lets whoever knows the password sign in without a code.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.audit import services as audit

from ...models import MfaDevice, User
from ...services import _studio_id


class Command(BaseCommand):
    help = "Disable MFA for an account that lost its authenticator and recovery codes."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("email")

    def handle(self, *args: Any, **options: Any) -> None:
        user = User.objects.filter(email__iexact=options["email"].strip()).first()
        if user is None:
            raise CommandError("No such account.")
        removed, _ = MfaDevice.objects.filter(user=user).delete()
        if not removed:
            raise CommandError("MFA is not enabled for this account.")
        audit.record(audit.Action.MFA_RESET_BY_OPERATOR, target=user, studio_id=_studio_id(user))
        self.stdout.write(f"MFA removed for user #{user.pk}.")
