"""Dati (fase 9): gli eventi già elaborati risultano "applied", non "pending".

Separata dalla migrazione dello schema di proposito: PostgreSQL rifiuta ALTER TABLE con controlli
di chiave esterna differiti ancora in sospeso nella stessa transazione (CLAUDE.md, gotcha).
"""

from django.db import migrations


def backfill(apps, schema_editor):
    WebhookEvent = apps.get_model("payments", "WebhookEvent")
    WebhookEvent.objects.filter(processed_at__isnull=False, outcome="pending").update(
        outcome="applied"
    )


class Migration(migrations.Migration):
    dependencies = [("payments", "0007_phase9_connect_schema")]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
