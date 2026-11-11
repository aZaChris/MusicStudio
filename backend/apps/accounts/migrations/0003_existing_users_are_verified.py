"""Accounts created before phase 7 (commands, seed, admin) were made by the operator for a
known address: treat them as confirmed so nobody is locked out by the upgrade.
Kept apart from the schema change (CLAUDE.md: PostgreSQL and deferred FK checks)."""

from django.db import migrations


def verify_existing(apps, schema_editor):  # type: ignore[no-untyped-def]
    apps.get_model("accounts", "User").objects.update(email_verified=True)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_security_fields")]

    operations = [migrations.RunPython(verify_existing, migrations.RunPython.noop)]
