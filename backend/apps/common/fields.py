"""Cifratura a livello di applicazione per il testo libero (ADR-030, constitution X).

`EncryptedTextField` salva un token Fernet (AES-128-CBC + HMAC-SHA256, autenticato) e ridà al
codice Python il testo in chiaro. Le chiavi vengono da `FIELD_ENCRYPTION_KEYS`: la prima cifra,
tutte decifrano, così si può aggiungere una chiave nuova prima di ritirare la vecchia
(`manage.py rotate_field_keys`).

I valori cifrati non si possono cercare, filtrare o ordinare in SQL: usare il campo solo per
testi che si leggono per intero, come le note delle lezioni.
Spiegazione: docs/learning/concetti/cifratura-dei-campi.md.
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
    """Il cifrario per le chiavi configurate (in cache per elenco di chiavi, i test le cambiano)."""
    return _fernet(tuple(settings.FIELD_ENCRYPTION_KEYS))


def encrypt(value: str) -> str:
    return fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return fernet().decrypt(token.encode()).decode()


class EncryptedTextField(models.TextField):
    """Un TextField il cui contenuto è cifrato a riposo. Il testo vuoto resta vuoto."""

    def get_prep_value(self, value: Any) -> Any:
        # Python -> database: si cifra poco prima di scrivere.
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return encrypt(str(value))

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        # Database -> Python: si decifra appena letto, il resto del codice vede il testo in chiaro.
        if value is None or value == "":
            return value
        return decrypt(value)
