# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0006_expulsions_dsf_convocations.py

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("logement", "0005_prevention_expulsions"),
        ("mds", "0009_secteur_mds"),
        ("planning", "0004_ateliers"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="dossierexpulsion",
            name="numero_exploc",
            field=models.CharField(
                blank=True,
                help_text="Numéro de la procédure dans l'application de la préfecture.",
                max_length=30,
                verbose_name="N° de dossier EXPLOC",
            ),
        ),
        migrations.AddField(
            model_name="dossierexpulsion",
            name="proprietaire_email",
            field=models.EmailField(
                blank=True,
                help_text="Pour lui envoyer le questionnaire par mail plutôt que par courrier.",
                max_length=254,
                verbose_name="Mail du bailleur",
            ),
        ),
        migrations.AddField(
            model_name="dossierexpulsion",
            name="questionnaire_bailleur_le",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="Questionnaire envoyé au bailleur le",
            ),
        ),
        migrations.AddField(
            model_name="dossierexpulsion",
            name="questionnaire_bailleur_retour",
            field=models.DateField(
                blank=True, null=True, verbose_name="Questionnaire du bailleur reçu le"
            ),
        ),
        migrations.AddField(
            model_name="dossierexpulsion",
            name="questionnaire_retour_avant",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="Retour du questionnaire souhaité avant le",
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
        migrations.AlterField(
            model_name="formulaireofficiel",
            name="code",
            field=models.CharField(
                choices=[
                    ("FSL_ACCES", "Demande d'aide à l'accès au logement"),
                    ("FSL_AVIS", "Avis motivé et proposition du travailleur social"),
                    (
                        "FSL_ARGUMENTAIRE",
                        "Argumentaire de pièces manquantes (note du cadre)",
                    ),
                    ("FSL_PRET", "Contrat de prêt"),
                    ("FSL_GARANTIE", "Contrat de mise en jeu de la garantie"),
                    ("FSL_PRELEVEMENT", "Autorisation de prélèvement"),
                    ("FSL_CONVENTION", "Convention d'accès au logement"),
                    (
                        "FSL_IDENT_LOGEMENT",
                        "Fiche d'identification du logement (bailleur privé)",
                    ),
                    ("FSL_PIECES", "Liste des pièces à fournir"),
                    (
                        "CERFA_11362",
                        "Demande de versement direct de l'allocation de logement (Cerfa 11362)",
                    ),
                    ("FSL_EAU", "Demande d'aide aux impayés d'eau"),
                    ("FSL_ENERGIE", "Demande d'aide aux impayés d'électricité, de gaz"),
                    (
                        "FSL_AVIS_FLUIDES",
                        "Avis motivé du travailleur social (énergie, eau)",
                    ),
                    (
                        "FSL_ARGU_FLUIDES",
                        "Argumentaire de pièces manquantes, énergie et eau (note du cadre)",
                    ),
                    ("FSL_MAINTIEN", "Demande FSL maintien ou concordat"),
                    (
                        "FSL_ARGU_MAINTIEN",
                        "Argumentaire de pièces manquantes, maintien et concordat (note du cadre)",
                    ),
                    ("FSL_ENGAGEMENTS", "Engagements du locataire et du bailleur"),
                    (
                        "FSL_CONCORDAT",
                        "Concordat – convention de résorption de dette locative",
                    ),
                    ("FSL_PIECES_MAINTIEN", "Liste des pièces à fournir (maintien)"),
                    (
                        "COPP_FICHE_1",
                        "Commission publics prioritaires (COPP) – fiche de saisine, page 1",
                    ),
                    (
                        "COPP_FICHE_2",
                        "Commission publics prioritaires (COPP) – fiche de saisine, page 2",
                    ),
                    (
                        "EXP_DSF",
                        "Expulsions – diagnostic social et financier (Cerfa 16227) : remplace celui livré avec CID",
                    ),
                    (
                        "EXP_QUEST_BAILLEUR",
                        "Expulsions – questionnaire bailleur pour le DSF",
                    ),
                    ("EXP_CARENCE", "Expulsions – bordereau de carence"),
                ],
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="ConvocationExpulsion",
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
                    "type_convocation",
                    models.CharField(
                        choices=[
                            ("DSF_1", "1re convocation (DSF)"),
                            ("DSF_2", "2e et dernière convocation (DSF)"),
                        ],
                        default="DSF_1",
                        max_length=6,
                    ),
                ),
                (
                    "date_courrier",
                    models.DateField(
                        default=django.utils.timezone.localdate,
                        verbose_name="Courrier du",
                    ),
                ),
                ("date_rdv", models.DateTimeField(verbose_name="Rendez-vous le")),
                (
                    "lieu",
                    models.CharField(
                        blank=True, help_text="Vide : la MDS", max_length=255
                    ),
                ),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("PREVUE", "Prévue"),
                            ("VENU", "Venu"),
                            ("ABSENT", "Absent"),
                            ("ANNULE", "Annulée ou reportée"),
                        ],
                        default="PREVUE",
                        max_length=7,
                    ),
                ),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                (
                    "agent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Reçu par",
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
                    "dossier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="convocations",
                        to="logement.dossierexpulsion",
                    ),
                ),
                (
                    "rdv",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="planning.creneaurdv",
                    ),
                ),
            ],
            options={
                "verbose_name": "Convocation (prévention des expulsions)",
                "verbose_name_plural": "Convocations (prévention des expulsions)",
                "ordering": ["date_rdv"],
            },
        ),
        migrations.CreateModel(
            name="DestinataireExpulsion",
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
                        help_text="Ex. « Tribunal judiciaire de … – greffe des contentieux de la protection »",
                        max_length=150,
                    ),
                ),
                (
                    "type_destinataire",
                    models.CharField(
                        choices=[
                            ("TRIBUNAL", "Greffe du tribunal"),
                            ("PREFECTURE", "Préfecture, sous-préfecture"),
                            ("AUTRE", "Autre"),
                        ],
                        default="TRIBUNAL",
                        max_length=10,
                    ),
                ),
                ("email", models.EmailField(max_length=254)),
                ("actif", models.BooleanField(default=True)),
                (
                    "mds",
                    models.ManyToManyField(
                        blank=True,
                        help_text="MDS qui transmettent à cette adresse ; vide : toutes.",
                        related_name="destinataires_expulsion",
                        to="mds.mds",
                    ),
                ),
            ],
            options={
                "verbose_name": "Destinataire des diagnostics (expulsions)",
                "verbose_name_plural": "Destinataires des diagnostics (expulsions)",
                "ordering": ["type_destinataire", "nom"],
            },
        ),
        migrations.CreateModel(
            name="DiagnosticExpulsion",
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
                    "type_document",
                    models.CharField(
                        choices=[
                            ("DSF", "Diagnostic social et financier"),
                            ("CARENCE", "Bordereau de carence"),
                        ],
                        default="DSF",
                        max_length=8,
                    ),
                ),
                ("donnees", models.JSONField(blank=True, default=dict)),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("BROUILLON", "En rédaction"),
                            ("A_VISER", "Visa du cadre demandé"),
                            ("VISE", "Visé par le cadre : prêt à envoyer"),
                            ("ENVOYE", "Transmis"),
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
                        related_name="diagnostics",
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
                "verbose_name": "Diagnostic social et financier (ou carence)",
                "verbose_name_plural": "Diagnostics sociaux et financiers (ou carences)",
                "ordering": ["-cree_le"],
            },
        ),
    ]
