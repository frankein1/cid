# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0008_commissions_expulsions.py

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("logement", "0007_durees_conservation"),
        ("mds", "0009_secteur_mds"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="convocationexpulsion",
            name="type_convocation",
            field=models.CharField(
                choices=[
                    ("DSF_1", "1re convocation (DSF)"),
                    ("DSF_2", "2e et dernière convocation (DSF)"),
                    ("COM_1", "Convocation avant commission"),
                    ("COM_2", "Relance avant commission"),
                ],
                default="DSF_1",
                max_length=6,
            ),
        ),
        migrations.AlterField(
            model_name="etapeexpulsion",
            name="type_etape",
            field=models.CharField(
                choices=[
                    ("SIGNALEMENT", "Signalement (CCAPEX, CAF, bailleur)"),
                    ("COMMANDEMENT_PAYER", "Commandement de payer"),
                    ("ASSIGNATION", "Assignation"),
                    ("QUESTIONNAIRE_BAILLEUR", "Questionnaire envoyé au bailleur"),
                    ("DSF", "Diagnostic social et financier transmis"),
                    ("CARENCE", "Bordereau de carence transmis"),
                    ("AUDIENCE", "Audience"),
                    ("JUGEMENT", "Jugement"),
                    ("SIGNIFICATION", "Signification du jugement"),
                    ("PLAN_APUREMENT", "Plan d'apurement, protocole"),
                    ("COMMANDEMENT_QUITTER", "Commandement de quitter les lieux"),
                    ("DEMANDE_CFP", "Demande de concours de la force publique"),
                    ("CAPEX_LOCALE", "CAPEX locale"),
                    ("COMMISSION_PREFECTORALE", "Commission préfectorale"),
                    ("CFP_ACCORDE", "Concours de la force publique accordé"),
                    ("EXPULSION", "Expulsion réalisée"),
                    ("RELOGEMENT", "Relogement, solution trouvée"),
                    ("AUTRE", "Autre"),
                ],
                max_length=25,
                verbose_name="Étape",
            ),
        ),
        migrations.CreateModel(
            name="CommissionExpulsion",
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
                    "type_commission",
                    models.CharField(
                        choices=[
                            ("LOCALE", "CAPEX locale"),
                            ("PREFECTORALE", "Commission préfectorale"),
                            ("CCAPEX", "CCAPEX"),
                        ],
                        default="LOCALE",
                        max_length=12,
                        verbose_name="Instance",
                    ),
                ),
                (
                    "nom",
                    models.CharField(
                        help_text="Ex. « CAPEX locale Martigues – Port-de-Bouc »",
                        max_length=150,
                    ),
                ),
                ("date", models.DateField()),
                ("heure", models.CharField(blank=True, max_length=10)),
                ("lieu", models.CharField(blank=True, max_length=255)),
                (
                    "date_limite",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="Actualisations attendues le",
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True,
                        help_text="Proposé à l'envoi des actualisations.",
                        max_length=254,
                        verbose_name="Mail du secrétariat",
                    ),
                ),
                (
                    "tenue",
                    models.BooleanField(default=False, verbose_name="Séance tenue"),
                ),
                (
                    "compte_rendu",
                    models.TextField(blank=True, verbose_name="Observations générales"),
                ),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
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
                    models.ManyToManyField(
                        blank=True,
                        help_text="MDS concernées ; vide : toutes.",
                        related_name="commissions_expulsion",
                        to="mds.mds",
                    ),
                ),
            ],
            options={
                "verbose_name": "Commission (prévention des expulsions)",
                "verbose_name_plural": "Commissions (prévention des expulsions)",
                "ordering": ["-date"],
            },
        ),
        migrations.CreateModel(
            name="PassageCommission",
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
                ("actualisation", models.JSONField(blank=True, default=dict)),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("A_FAIRE", "Actualisation à faire"),
                            ("A_VISER", "Visa du cadre demandé"),
                            ("VISEE", "Visée : prête à transmettre"),
                            ("TRANSMISE", "Transmise"),
                        ],
                        default="A_FAIRE",
                        max_length=10,
                    ),
                ),
                (
                    "date_validation_cadre",
                    models.DateTimeField(blank=True, null=True, verbose_name="Visé le"),
                ),
                ("date_envoi", models.DateField(blank=True, null=True)),
                (
                    "avis",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("MAINTIEN", "Maintien dans les lieux, plan à respecter"),
                            ("DELAI", "Délai supplémentaire"),
                            (
                                "ORIENTATION",
                                "Orientation (relogement, hébergement, accompagnement)",
                            ),
                            (
                                "CFP_FAVORABLE",
                                "Avis favorable au concours de la force publique",
                            ),
                            (
                                "CFP_DEFAVORABLE",
                                "Avis défavorable au concours de la force publique",
                            ),
                            ("AJOURNE", "Ajourné, à revoir"),
                            ("AUTRE", "Autre"),
                        ],
                        max_length=20,
                        verbose_name="Avis de la commission",
                    ),
                ),
                (
                    "avis_detail",
                    models.TextField(blank=True, verbose_name="Préconisations"),
                ),
                ("historique", models.JSONField(blank=True, default=list)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
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
                    "commission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="passages",
                        to="logement.commissionexpulsion",
                    ),
                ),
                (
                    "dossier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="passages",
                        to="logement.dossierexpulsion",
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
                "verbose_name": "Dossier inscrit à une commission",
                "verbose_name_plural": "Dossiers inscrits aux commissions",
                "ordering": ["commission__date", "dossier__nom"],
                "unique_together": {("commission", "dossier")},
            },
        ),
        migrations.AddField(
            model_name="convocationexpulsion",
            name="passage",
            field=models.ForeignKey(
                blank=True,
                help_text="Convocation avant une commission",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="convocations",
                to="logement.passagecommission",
            ),
        ),
    ]
