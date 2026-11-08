# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0007_durees_conservation.py

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("logement", "0006_expulsions_dsf_convocations"),
    ]

    operations = [
        migrations.AddField(
            model_name="dossierexpulsion",
            name="anonymise_le",
            field=models.DateField(
                blank=True,
                editable=False,
                help_text="Durée de conservation atteinte : identité effacée, chiffres gardés.",
                null=True,
                verbose_name="Anonymisé le",
            ),
        ),
    ]
