import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("students", "0002_student_studio")]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="studio",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="students",
                to="studios.studio",
            ),
        ),
    ]
