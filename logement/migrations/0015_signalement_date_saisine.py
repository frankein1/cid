# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0015_signalement_date_saisine.py

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("logement", "0014_signalement_indigne_rdv_journal"),
    ]

    operations = [
        migrations.AddField(
            model_name="signalementhabitatindigne",
            name="date_saisine",
            field=models.DateField(
                blank=True, null=True, verbose_name="Date de saisine de la MDS"
            ),
        ),
    ]
