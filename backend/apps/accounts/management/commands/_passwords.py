"""Where a new account's password comes from. Never from the command line: that lands in
the shell history and in the process list."""

import os
from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError

ENV_VAR = "ACCOUNT_PASSWORD"


def read_password(email: str) -> str:
    """`ACCOUNT_PASSWORD` if set (scripts, a Coolify terminal), else asked twice on the terminal."""
    password = os.environ.get(ENV_VAR)
    if password is None:
        password = getpass(f"Password for {email}: ")
        if password != getpass("Again: "):
            raise CommandError("The two passwords differ.")
    try:
        validate_password(password)
    except ValidationError as error:
        raise CommandError("; ".join(error.messages)) from error
    return password
