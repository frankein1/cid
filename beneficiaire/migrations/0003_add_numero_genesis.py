# Generated manually for numero_genesis field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('beneficiaire', '0002_initial'),  # ← Pointe vers ta dernière migration
    ]

    operations = [
        migrations.AddField(
            model_name='beneficiaire',
            name='numero_genesis',
            field=models.CharField(
                blank=True,
                max_length=50,
                null=True,
                verbose_name="Numéro GENESIS",
                help_text="Numéro d'identification externe (GENESIS)"
            ),
        ),
    ]
