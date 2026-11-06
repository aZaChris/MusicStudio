import django.db.models.deletion
from django.db import migrations, models
from django.db.models import OuterRef, Subquery


def copy_studio_from_teacher(apps, schema_editor):
    Student = apps.get_model("students", "Student")
    Teacher = apps.get_model("studios", "Teacher")
    Student.objects.update(
        studio_id=Subquery(Teacher.objects.filter(pk=OuterRef("teacher_id")).values("studio_id")[:1])
    )


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0001_initial"),
        ("studios", "0004_teacher_studio_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="studio",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="students",
                to="studios.studio",
            ),
        ),
        migrations.RunPython(copy_studio_from_teacher, migrations.RunPython.noop),
    ]
