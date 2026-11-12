# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0014_signalement_indigne_rdv_journal.py

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("beneficiaire", "0014_cles_recherche_annuaire"),
        ("logement", "0013_signalement_habitat_indigne"),
        ("planning", "0004_ateliers"),
    ]

    operations = [
        migrations.AddField(
            model_name="signalementhabitatindigne",
            name="creneau",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="signalements_indigne",
                to="planning.creneaurdv",
                verbose_name="Visite (rendez-vous du planning)",
            ),
        ),
        migrations.AddField(
            model_name="signalementhabitatindigne",
            name="entretien",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="signalements_indigne",
                to="beneficiaire.entretiensocial",
                verbose_name="Entrée du journal",
            ),
        ),
    ]
