# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# mds/migrations/0009_secteur_mds.py

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mds", "0008_signature_agent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mds",
            name="communes",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Villes, arrondissements ou codes postaux couverts (ex. « Port-de-Bouc », « 13001 », « Marseille 3e ») ; les codes INSEE sont aussi reconnus. Sert à proposer la MDS d'après une adresse.",
                verbose_name="Secteur",
            ),
        ),
    ]
