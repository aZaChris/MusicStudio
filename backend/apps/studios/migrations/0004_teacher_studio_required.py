import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("studios", "0003_personal_studios")]

    operations = [
        migrations.AlterField(
            model_name="teacher",
            name="studio",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="teachers",
                to="studios.studio",
            ),
        ),
    ]
