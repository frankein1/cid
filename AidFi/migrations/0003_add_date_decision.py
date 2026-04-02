from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("AidFi", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="decisionafase",
            name="date_decision",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
            ),
        ),
    ]
