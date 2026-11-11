"""Application-level encryption of free text (ADR-030, constitution X).

`EncryptedTextField` stores a Fernet token (AES-128-CBC + HMAC-SHA256, authenticated) and
gives Python code the plain text back. Keys come from `FIELD_ENCRYPTION_KEYS`: the first
encrypts, every key decrypts, so a new key can be added before the old one is retired
(`manage.py rotate_field_keys`).

Encrypted values cannot be searched, filtered or ordered in SQL: use it only for text that
is read whole, such as lesson notes.
"""

from functools import cache
from typing import Any

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.db import models


@cache
def _fernet(keys: tuple[str, ...]) -> MultiFernet:
    return MultiFernet([Fernet(key) for key in keys])


def fernet() -> MultiFernet:
    """The cipher for the configured keys (cached per key list, so tests can swap keys)."""
    return _fernet(tuple(settings.FIELD_ENCRYPTION_KEYS))


def encrypt(value: str) -> str:
    return fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return fernet().decrypt(token.encode()).decode()


class EncryptedTextField(models.TextField):
    """A TextField whose content is encrypted at rest. Empty text stays empty (not secret)."""

    def get_prep_value(self, value: Any) -> Any:
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return encrypt(str(value))

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if value is None or value == "":
            return value
        return decrypt(value)
