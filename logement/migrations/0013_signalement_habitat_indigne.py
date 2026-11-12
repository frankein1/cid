# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0013_signalement_habitat_indigne.py

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("beneficiaire", "0014_cles_recherche_annuaire"),
        ("logement", "0012_merge_dsf_hebergement"),
        ("mds", "0009_secteur_mds"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SignalementHabitatIndigne",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "origine",
                    models.CharField(
                        choices=[
                            ("VAD", "Visite à domicile du TS"),
                            ("LOCATAIRE", "Signalement du locataire"),
                            ("BAILLEUR", "Signalement du bailleur"),
                            ("COMMUNE", "Signalement de la commune"),
                            ("AUTRE", "Autre"),
                        ],
                        default="VAD",
                        max_length=12,
                    ),
                ),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("BROUILLON", "En préparation"),
                            ("ENVOYE", "Envoyé au PDLHI"),
                            ("CLOS", "Clos"),
                        ],
                        default="BROUILLON",
                        max_length=12,
                    ),
                ),
                (
                    "donnees",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Rubriques 1 à 8 de la fiche PDLHI",
                    ),
                ),
                (
                    "permis_ville",
                    models.BooleanField(
                        default=False, verbose_name="Ville soumise au permis de louer"
                    ),
                ),
                (
                    "permis_logement",
                    models.BooleanField(
                        default=False, verbose_name="Logement soumis au permis de louer"
                    ),
                ),
                (
                    "rapport_vad",
                    models.TextField(blank=True, verbose_name="Rapport de VAD"),
                ),
                ("vad_date_signature", models.DateTimeField(blank=True, null=True)),
                ("fiche_date_signature", models.DateTimeField(blank=True, null=True)),
                (
                    "date_envoi",
                    models.DateField(
                        blank=True, null=True, verbose_name="Date d'envoi au PDLHI"
                    ),
                ),
                (
                    "reponse_pdlhi",
                    models.TextField(blank=True, verbose_name="Réponse du PDLHI"),
                ),
                (
                    "enquete_salubrite",
                    models.BooleanField(
                        default=False, verbose_name="Enquête de salubrité"
                    ),
                ),
                ("suite", models.TextField(blank=True, verbose_name="Suite donnée")),
                (
                    "bascule_dalo",
                    models.BooleanField(
                        default=False, verbose_name="Bascule sur dispositif DALO"
                    ),
                ),
                ("historique", models.JSONField(blank=True, default=list)),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                ("date_modification", models.DateTimeField(auto_now=True)),
                (
                    "beneficiaire",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="signalements_indigne",
                        to="beneficiaire.beneficiaire",
                    ),
                ),
                (
                    "cree_par",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="signalements_indigne_crees",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "fiche_signee_par",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="fiches_signees_indigne",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "mds",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="signalements_indigne",
                        to="mds.mds",
                    ),
                ),
                (
                    "vad_signee_par",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="vad_signees_indigne",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Signalement d'habitat indigne",
                "verbose_name_plural": "Signalements d'habitat indigne",
                "ordering": ["-date_creation"],
            },
        ),
    ]
