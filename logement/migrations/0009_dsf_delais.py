# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0009_dsf_delais.py

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("logement", "0008_commissions_expulsions"),
    ]

    operations = [
        migrations.AddField(
            model_name="dossierexpulsion",
            name="observations_locataire",
            field=models.BooleanField(
                default=False,
                help_text="Pour le DSF : sans observation, le bordereau de carence peut suivre.",
                verbose_name="Le locataire a transmis des observations",
            ),
        ),
    ]
