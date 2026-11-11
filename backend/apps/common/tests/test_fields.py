"""Encrypted text: plain in Python, unreadable in the database, readable after key rotation."""

import pytest
from cryptography.fernet import Fernet, InvalidToken
from django.db import connection

from apps.common import fields
from apps.common.factories import LessonFactory

pytestmark = pytest.mark.django_db


def _raw_notes(lesson_id: int) -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT notes FROM lessons_lesson WHERE id = %s", [lesson_id])
        return cursor.fetchone()[0]


def test_round_trip_and_ciphertext_at_rest():
    lesson = LessonFactory(notes="Fatica con il pollice sinistro")

    lesson.refresh_from_db()

    assert lesson.notes == "Fatica con il pollice sinistro"
    raw = _raw_notes(lesson.id)
    assert raw.startswith("gAAAA")
    assert "pollice" not in raw


def test_empty_text_is_stored_empty():
    lesson = LessonFactory(notes="")

    assert _raw_notes(lesson.id) == ""


def test_old_key_still_decrypts_after_rotation(settings):
    old_key = settings.FIELD_ENCRYPTION_KEYS[0]
    lesson = LessonFactory(notes="scritta con la chiave vecchia")
    settings.FIELD_ENCRYPTION_KEYS = [Fernet.generate_key().decode(), old_key]

    lesson.refresh_from_db()

    assert lesson.notes == "scritta con la chiave vecchia"


def test_unknown_key_cannot_read(settings):
    token = fields.encrypt("segreto")
    settings.FIELD_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]

    with pytest.raises(InvalidToken):
        fields.decrypt(token)


def test_data_migration_encrypts_plain_rows_once():
    from importlib import import_module
    from types import SimpleNamespace

    migration = import_module("apps.lessons.migrations.0007_encrypt_existing_notes")
    lesson = LessonFactory(notes="")
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE lessons_lesson SET notes = 'testo in chiaro' WHERE id = %s", [lesson.id]
        )
    editor = SimpleNamespace(connection=connection)

    migration.encrypt_notes(None, editor)
    first = _raw_notes(lesson.id)
    migration.encrypt_notes(None, editor)  # idempotent

    assert first.startswith("gAAAA") and _raw_notes(lesson.id) == first
    lesson.refresh_from_db()
    assert lesson.notes == "testo in chiaro"

    migration.decrypt_notes(None, editor)
    assert _raw_notes(lesson.id) == "testo in chiaro"


def test_rotate_field_keys_moves_data_to_the_new_key(settings):
    from django.core.management import call_command

    old_key = settings.FIELD_ENCRYPTION_KEYS[0]
    lesson = LessonFactory(notes="da ruotare")
    new_key = Fernet.generate_key().decode()
    settings.FIELD_ENCRYPTION_KEYS = [new_key, old_key]

    call_command("rotate_field_keys", stdout=open("/dev/null", "w"))  # noqa: SIM115
    settings.FIELD_ENCRYPTION_KEYS = [new_key]  # old key retired

    lesson.refresh_from_db()
    assert lesson.notes == "da ruotare"
