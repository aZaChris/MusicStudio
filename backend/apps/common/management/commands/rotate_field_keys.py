"""Re-encrypt every encrypted field with the first key of FIELD_ENCRYPTION_KEYS (ADR-030).

Rotation: put the new key first (keep the old one after it), deploy, run this command,
then remove the old key and deploy again. Raw SQL in batches: no model save, so no
`updated_at` bump and no signals. Safe to run twice.
"""

from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.common.fields import EncryptedTextField, fernet

BATCH = 500


class Command(BaseCommand):
    help = "Re-encrypt encrypted fields with the current primary key."

    def handle(self, *args: Any, **options: Any) -> None:
        cipher = fernet()
        for model in apps.get_models():
            table = model._meta.db_table
            for field in model._meta.concrete_fields:
                if not isinstance(field, EncryptedTextField):
                    continue
                column = connection.ops.quote_name(field.get_attname_column()[1] or field.name)
                quoted = connection.ops.quote_name(table)
                total, last_id = 0, 0
                while True:
                    with transaction.atomic(), connection.cursor() as cursor:
                        cursor.execute(
                            f"SELECT id, {column} FROM {quoted} "  # noqa: S608 - names from models
                            f"WHERE id > %s AND {column} <> '' ORDER BY id LIMIT %s",
                            [last_id, BATCH],
                        )
                        rows = cursor.fetchall()
                        if not rows:
                            break
                        cursor.executemany(
                            f"UPDATE {quoted} SET {column} = %s WHERE id = %s",  # noqa: S608
                            [(cipher.rotate(value.encode()).decode(), pk) for pk, value in rows],
                        )
                    total += len(rows)
                    last_id = rows[-1][0]
                self.stdout.write(f"{table}.{field.column}: {total} values re-encrypted")
