"""Da dove viene la password di un account nuovo. Mai dalla riga di comando: finirebbe nella
cronologia della shell e nell'elenco dei processi."""

import os
from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError

ENV_VAR = "ACCOUNT_PASSWORD"


def read_password(email: str) -> str:
    """`ACCOUNT_PASSWORD` se impostata (script, terminale Coolify), altrimenti chiesta due volte."""
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
