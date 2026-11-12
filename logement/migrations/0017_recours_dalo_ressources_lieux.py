# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0017_recours_dalo_ressources_lieux.py

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("logement", "0016_recours_dalo"),
    ]

    operations = [
        migrations.AddField(
            model_name="recoursdalo",
            name="ressources_mois",
            field=models.CharField(blank=True, max_length=40, verbose_name="6. Ressources mensuelles du mois de"),
        ),
        migrations.AddField(
            model_name="recoursdalo",
            name="ressources",
            field=models.JSONField(blank=True, default=dict, help_text="Clé « NATURE|vous », « NATURE|p1 »… → montant mensuel", verbose_name="6. Ressources mensuelles"),
        ),
        migrations.AddField(
            model_name="recoursdalo",
            name="ressources_annee_avis",
            field=models.CharField(blank=True, max_length=4, verbose_name="6. Année du dernier avis d'impôt"),
        ),
        migrations.AddField(
            model_name="recoursdalo",
            name="pcb",
            field=models.CharField(blank=True, choices=[("OUI", "Oui"), ("NON", "Non")], max_length=3, verbose_name="6. Aidé par un point conseil budget"),
        ),
        migrations.AddField(
            model_name="recoursdalo",
            name="surendettement",
            field=models.CharField(blank=True, choices=[("OUI", "Oui"), ("NON", "Non")], max_length=3, verbose_name="6. Dossier de surendettement déposé"),
        ),
        migrations.AddField(
            model_name="recoursdalo",
            name="lieux_travail",
            field=models.JSONField(blank=True, default=list, help_text="Ligne 0 : vous-même ; lignes 1 à 7 : personnes du tableau 5", verbose_name="7. Lieux de travail ou d'activité"),
        ),
    ]
