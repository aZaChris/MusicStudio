"""Validation of the field-encryption keys, shared by settings and tests."""

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

DEV_ONLY_KEY = "ZGV2LW9ubHktaW5zZWN1cmUtZmllbGQta2V5LTAwMDA="


def check_field_keys(keys: list[str]) -> None:
    """Refuse an empty list, the public dev key, or anything that is not a Fernet key."""
    if not keys:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS must hold at least one key.")
    for key in keys:
        if key == DEV_ONLY_KEY:
            raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS uses the public dev-only key.")
        try:
            Fernet(key)
        except ValueError as exc:
            raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS holds an invalid key.") from exc
