"""Phase 2, step 1: enable btree_gist and add a stored end_time, backfilled from duration.

The NOT NULL change and the constraints are in 0005 so each step runs in its own
transaction (PostgreSQL refuses ALTER TABLE while deferred FK checks from the UPDATE are
pending).
"""

from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("lessons", "0003_lesson_indexes")]

    operations = [
        # Needs a role allowed to CREATE EXTENSION (the Compose/CI Postgres superuser is).
        BtreeGistExtension(),
        migrations.AddField(
            model_name="lesson", name="end_time", field=models.DateTimeField(null=True)
        ),
        migrations.RunSQL(
            "UPDATE lessons_lesson SET end_time = start_time + duration_minutes * interval '1 minute'",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
