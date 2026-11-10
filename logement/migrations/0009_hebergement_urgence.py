# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0009_hebergement_urgence.py

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("beneficiaire", "0014_cles_recherche_annuaire"),
        ("logement", "0008_commissions_expulsions"),
        ("mds", "0009_secteur_mds"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DestinataireHebergement",
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
                    "nom",
                    models.CharField(
                        help_text="Ex. « Service d'appui à l'hébergement »",
                        max_length=150,
                    ),
                ),
                ("email", models.EmailField(max_length=254)),
                ("actif", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Destinataire des fiches d'hébergement d'urgence",
                "verbose_name_plural": "Destinataires des fiches d'hébergement d'urgence",
                "ordering": ["nom"],
            },
        ),
        migrations.CreateModel(
            name="StructureHebergement",
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
                ("nom", models.CharField(max_length=150)),
                ("ville", models.CharField(blank=True, max_length=100)),
                (
                    "public",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Public accueilli"
                    ),
                ),
                (
                    "duree_initiale_jours",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="Durée d'accueil (jours)"
                    ),
                ),
                (
                    "duree_renouvellement_jours",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Durée d'un renouvellement (jours)",
                    ),
                ),
                (
                    "contact",
                    models.TextField(blank=True, verbose_name="Contact (interne)"),
                ),
                ("actif", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Structure d'hébergement d'urgence",
                "verbose_name_plural": "Structures d'hébergement d'urgence",
                "ordering": ["nom"],
            },
        ),
        migrations.CreateModel(
            name="DossierHebergement",
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
                    "numero",
                    models.CharField(editable=False, max_length=14, unique=True),
                ),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("RECHERCHE", "Recherche d'une solution"),
                            ("HEBERGE", "Hébergé en structure"),
                            ("CLOS", "Clos"),
                        ],
                        default="RECHERCHE",
                        max_length=10,
                    ),
                ),
                (
                    "date_ouverture",
                    models.DateField(default=django.utils.timezone.localdate),
                ),
                (
                    "structure_libre",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="Autre structure"
                    ),
                ),
                (
                    "date_entree",
                    models.DateField(
                        blank=True, null=True, verbose_name="Entrée dans la structure"
                    ),
                ),
                (
                    "date_fin_prevue",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="Fin de prise en charge prévue",
                    ),
                ),
                (
                    "date_sortie",
                    models.DateField(
                        blank=True, null=True, verbose_name="Sortie de la structure"
                    ),
                ),
                (
                    "motif_cloture",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("LOGEMENT", "Accès à un logement"),
                            ("HEBERGEMENT", "Hébergement durable (CHRS, résidence…)"),
                            ("MATERNEL", "Centre maternel"),
                            ("PERSONNELLE", "Solution personnelle (famille, amis)"),
                            ("ETAT", "Prise en charge par les services de l'État"),
                            ("SANS_SUITE", "Demande sans suite ou refusée"),
                            ("PERDU_DE_VUE", "Ménage perdu de vue"),
                            ("DEPART", "Départ de la structure sans solution connue"),
                            ("AUTRE", "Autre"),
                        ],
                        max_length=14,
                    ),
                ),
                ("date_cloture", models.DateField(blank=True, null=True)),
                (
                    "alerte_pour",
                    models.DateField(
                        blank=True,
                        editable=False,
                        help_text="Échéance pour laquelle le référent a déjà été prévenu",
                        null=True,
                    ),
                ),
                (
                    "anonymise_le",
                    models.DateField(blank=True, editable=False, null=True),
                ),
                ("historique", models.JSONField(blank=True, default=list)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                (
                    "beneficiaire",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dossiers_hebergement",
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
                    "mds",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="dossiers_hebergement",
                        to="mds.mds",
                    ),
                ),
                (
                    "referent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Référent social",
                    ),
                ),
                (
                    "structure",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dossiers",
                        to="logement.structurehebergement",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dossier d'hébergement d'urgence",
                "verbose_name_plural": "Dossiers d'hébergement d'urgence",
                "ordering": ["-date_ouverture", "-pk"],
            },
        ),
        migrations.CreateModel(
            name="DemarcheHebergement",
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
                    "type_demarche",
                    models.CharField(
                        choices=[
                            ("115", "Appel au 115"),
                            ("SIAO", "Fiche SIAO instruite ou mise à jour"),
                            ("CENTRE_MATERNEL", "Centre maternel"),
                            ("MECS", "Accueil mère-enfants (MECS, foyer)"),
                            ("DAHO", "Recours DAHO"),
                            ("DALO", "Recours DALO"),
                            ("RESEAU", "Solution personnelle (famille, amis, hôtel)"),
                            ("AUTRE", "Autre"),
                        ],
                        max_length=16,
                    ),
                ),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                (
                    "precision",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="Précision (lequel ?)"
                    ),
                ),
                (
                    "reponse",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Réponse, proposition"
                    ),
                ),
                (
                    "saisi_par",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "dossier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="demarches",
                        to="logement.dossierhebergement",
                    ),
                ),
            ],
            options={
                "verbose_name": "Démarche d'hébergement",
                "verbose_name_plural": "Démarches d'hébergement",
                "ordering": ["date", "pk"],
            },
        ),
        migrations.CreateModel(
            name="FicheHebergement",
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
                    "type_fiche",
                    models.CharField(
                        choices=[
                            ("SAS", "Demande d'hébergement d'urgence"),
                            ("RENOUV", "Renouvellement de la prise en charge"),
                            ("FINAL", "Rapport final de prise en charge"),
                            ("ETAT", "Orientation vers les services de l'État (DDETS)"),
                        ],
                        default="SAS",
                        max_length=6,
                    ),
                ),
                ("donnees", models.JSONField(blank=True, default=dict)),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("BROUILLON", "En rédaction"),
                            ("A_VISER", "Visa du cadre demandé"),
                            ("VISEE", "Visée par le cadre : prête à envoyer"),
                            ("ENVOYEE", "Transmise"),
                        ],
                        default="BROUILLON",
                        max_length=10,
                    ),
                ),
                (
                    "date_validation_cadre",
                    models.DateTimeField(blank=True, null=True, verbose_name="Visé le"),
                ),
                ("date_envoi", models.DateField(blank=True, null=True)),
                (
                    "reponse",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("ACCORD", "Accord"),
                            ("AJOURNEMENT", "Ajournement (à compléter)"),
                            ("REFUS", "Refus ou pas de place"),
                        ],
                        max_length=12,
                    ),
                ),
                ("date_reponse", models.DateField(blank=True, null=True)),
                ("reponse_detail", models.CharField(blank=True, max_length=255)),
                ("historique", models.JSONField(blank=True, default=list)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                ("modifie_le", models.DateTimeField(auto_now=True)),
                (
                    "cadre",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Visé par",
                    ),
                ),
                (
                    "dossier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fiches",
                        to="logement.dossierhebergement",
                    ),
                ),
                (
                    "redacteur",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Fiche d'hébergement d'urgence",
                "verbose_name_plural": "Fiches d'hébergement d'urgence",
                "ordering": ["-cree_le"],
            },
        ),
    ]
