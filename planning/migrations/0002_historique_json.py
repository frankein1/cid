from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planning', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='historiquecreneau',
            name='anciennes_valeurs',
            field=models.JSONField(default=dict, blank=True),
        ),
        migrations.AddField(
            model_name='historiquecreneau',
            name='nouvelles_valeurs',
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
