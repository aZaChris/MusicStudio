"""Phase 2, step 2: end_time required, duration column dropped, overlap constraints.

Fails loudly (IntegrityError) if existing data already contains overlapping active
lessons, instead of silently changing anything.
"""

import django.contrib.postgres.constraints
import django.contrib.postgres.fields.ranges
from django.db import migrations, models

import apps.lessons.models


class Migration(migrations.Migration):
    dependencies = [("lessons", "0004_lesson_end_time")]

    operations = [
        migrations.AlterField(
            model_name="lesson", name="end_time", field=models.DateTimeField()
        ),
        migrations.RemoveField(model_name="lesson", name="duration_minutes"),
        migrations.AddConstraint(
            model_name="lesson",
            constraint=models.CheckConstraint(
                condition=models.Q(("end_time__gt", models.F("start_time"))),
                name="lesson_end_after_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="lesson",
            constraint=django.contrib.postgres.constraints.ExclusionConstraint(
                condition=models.Q(("status__in", ("scheduled", "completed"))),
                expressions=[
                    (
                        apps.lessons.models.TsTzRange(
                            "start_time",
                            "end_time",
                            django.contrib.postgres.fields.ranges.RangeBoundary(),
                        ),
                        "&&",
                    ),
                    ("teacher", "="),
                ],
                name="lesson_no_teacher_overlap",
            ),
        ),
        migrations.AddConstraint(
            model_name="lesson",
            constraint=django.contrib.postgres.constraints.ExclusionConstraint(
                condition=models.Q(("status__in", ("scheduled", "completed"))),
                expressions=[
                    (
                        apps.lessons.models.TsTzRange(
                            "start_time",
                            "end_time",
                            django.contrib.postgres.fields.ranges.RangeBoundary(),
                        ),
                        "&&",
                    ),
                    ("student", "="),
                ],
                name="lesson_no_student_overlap",
            ),
        ),
    ]
