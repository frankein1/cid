# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0010_orientation_asell.py

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("beneficiaire", "0014_cles_recherche_annuaire"),
        ("logement", "0009_hebergement_urgence"),
        ("mds", "0009_secteur_mds"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OperateurASELL",
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
                ("sigle", models.CharField(max_length=60)),
                ("nom", models.CharField(max_length=150)),
                ("adresse", models.CharField(blank=True, max_length=255)),
                (
                    "cp_ville",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="Code postal et ville"
                    ),
                ),
                (
                    "telephone",
                    models.CharField(
                        blank=True, max_length=30, verbose_name="Téléphone"
                    ),
                ),
                (
                    "emails",
                    models.CharField(
                        blank=True,
                        help_text="Une ou plusieurs, séparées par des virgules : toutes sont proposées à l'envoi.",
                        max_length=255,
                        verbose_name="Adresses mail",
                    ),
                ),
                (
                    "nature",
                    models.CharField(
                        choices=[
                            ("ASELL", "ASELL (accompagnement individuel)"),
                            ("ASC", "ASC (action collective)"),
                            ("ALL", "ALL (auto-réhabilitation)"),
                        ],
                        default="ASELL",
                        max_length=5,
                    ),
                ),
                (
                    "thematique",
                    models.CharField(
                        choices=[
                            ("GENERALISTE", "Généraliste"),
                            ("RENFORCE", "Renforcé"),
                            ("COURTE_DUREE", "Diagnostic courte durée"),
                            ("ATELIERS", "Ateliers recherche logement"),
                            ("AUTO_REHAB", "Auto-réhabilitation accompagnée"),
                        ],
                        default="GENERALISTE",
                        max_length=12,
                        verbose_name="Thématique",
                    ),
                ),
                (
                    "territoire",
                    models.TextField(
                        blank=True,
                        help_text="Tel qu'écrit dans la liste : communes, « 13e et 14e arrondissements de Marseille », « Département »…",
                    ),
                ),
                (
                    "public_specifique",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Public spécifique"
                    ),
                ),
                (
                    "annee",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="Année de la convention"
                    ),
                ),
                ("actif", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Opérateur conventionné (ASELL)",
                "verbose_name_plural": "Opérateurs conventionnés (ASELL)",
                "ordering": ["sigle", "thematique", "pk"],
            },
        ),
        migrations.CreateModel(
            name="OrientationASELL",
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
                    "type_mesure",
                    models.CharField(
                        choices=[
                            ("GENERALISTE", "ASELL généraliste"),
                            ("RENFORCE", "ASELL renforcé"),
                        ],
                        default="GENERALISTE",
                        max_length=12,
                    ),
                ),
                (
                    "volet",
                    models.CharField(
                        choices=[("ACCES", "Accès"), ("MAINTIEN", "Maintien")],
                        default="MAINTIEN",
                        max_length=8,
                    ),
                ),
                (
                    "operateur_libre",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="Autre opérateur"
                    ),
                ),
                ("donnees", models.JSONField(blank=True, default=dict)),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("BROUILLON", "En préparation"),
                            ("ENVOYEE", "Envoyée"),
                            ("ABANDONNEE", "Abandonnée"),
                        ],
                        default="BROUILLON",
                        max_length=10,
                    ),
                ),
                ("date_envoi", models.DateField(blank=True, null=True)),
                (
                    "reponse",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("ACCORD", "Mesure engagée"),
                            ("ATTENTE", "Liste d'attente"),
                            ("REFUS", "Orientation non retenue"),
                        ],
                        max_length=8,
                    ),
                ),
                ("date_reponse", models.DateField(blank=True, null=True)),
                ("reponse_detail", models.CharField(blank=True, max_length=255)),
                ("historique", models.JSONField(blank=True, default=list)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                ("modifie_le", models.DateTimeField(auto_now=True)),
                (
                    "beneficiaire",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="orientations_asell",
                        to="beneficiaire.beneficiaire",
                    ),
                ),
                (
                    "cree_par",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "dossier_expulsion",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="orientations_asell",
                        to="logement.dossierexpulsion",
                    ),
                ),
                (
                    "mds",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orientations_asell",
                        to="mds.mds",
                    ),
                ),
                (
                    "operateur",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="orientations",
                        to="logement.operateurasell",
                    ),
                ),
            ],
            options={
                "verbose_name": "Orientation ASELL",
                "verbose_name_plural": "Orientations ASELL",
                "ordering": ["-cree_le"],
            },
        ),
    ]
