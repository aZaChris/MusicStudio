"""Encrypt the notes written before the field became encrypted (ADR-030).

Raw SQL on purpose: the historical model would treat existing plain text as ciphertext on
read. Rows that already hold a Fernet token are skipped, so the migration can run twice.
Kept apart from the schema change (PostgreSQL and deferred FK checks, see CLAUDE.md).
"""

from django.db import migrations

from apps.common.fields import decrypt, encrypt

BATCH = 1000


def _convert(schema_editor, transform, needs) -> None:  # type: ignore[no-untyped-def]
    connection = schema_editor.connection
    last_id = 0
    while True:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, notes FROM lessons_lesson WHERE id > %s AND notes <> '' "
                "ORDER BY id LIMIT %s",
                [last_id, BATCH],
            )
            rows = cursor.fetchall()
            if not rows:
                return
            changed = [(transform(notes), pk) for pk, notes in rows if needs(notes)]
            if changed:
                cursor.executemany("UPDATE lessons_lesson SET notes = %s WHERE id = %s", changed)
            last_id = rows[-1][0]


def encrypt_notes(apps, schema_editor):  # type: ignore[no-untyped-def]
    _convert(schema_editor, encrypt, lambda notes: not notes.startswith("gAAAA"))


def decrypt_notes(apps, schema_editor):  # type: ignore[no-untyped-def]
    _convert(schema_editor, decrypt, lambda notes: notes.startswith("gAAAA"))


class Migration(migrations.Migration):
    dependencies = [("lessons", "0006_encrypt_notes_field")]

    operations = [migrations.RunPython(encrypt_notes, decrypt_notes)]
