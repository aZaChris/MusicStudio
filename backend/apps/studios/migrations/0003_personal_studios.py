"""Every teacher gets a studio (ADR-010): solo teachers receive a personal studio of one.

Data-only migration; the NOT NULL change is in 0004 so each runs in its own transaction
(PostgreSQL refuses ALTER TABLE while deferred FK checks from the UPDATEs are pending).
"""

from django.db import migrations


def create_personal_studios(apps, schema_editor):
    Studio = apps.get_model("studios", "Studio")
    Teacher = apps.get_model("studios", "Teacher")
    for teacher in Teacher.objects.filter(studio__isnull=True).select_related("user"):
        studio = Studio.objects.create(name=teacher.user.email)
        teacher.studio = studio
        teacher.is_owner = True
        teacher.save(update_fields=["studio", "is_owner"])
        studio.owner = teacher
        studio.save(update_fields=["owner"])


class Migration(migrations.Migration):
    dependencies = [("studios", "0002_teacher_owner_constraint")]

    operations = [migrations.RunPython(create_personal_studios, migrations.RunPython.noop)]
