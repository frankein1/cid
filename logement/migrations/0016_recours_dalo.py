# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0016_recours_dalo.py

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("beneficiaire", "0014_cles_recherche_annuaire"),
        ("logement", "0015_signalement_date_saisine"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RecoursDALO",
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
                    "civilite",
                    models.CharField(
                        blank=True,
                        choices=[("M", "Monsieur"), ("MME", "Madame")],
                        max_length=5,
                    ),
                ),
                ("nom_naissance", models.CharField(blank=True, max_length=60)),
                ("nom_usage", models.CharField(blank=True, max_length=60)),
                ("prenoms", models.CharField(blank=True, max_length=120)),
                (
                    "date_naissance",
                    models.CharField(blank=True, help_text="JJ/MM/AAAA", max_length=10),
                ),
                (
                    "nationalite",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("FR", "Française"),
                            ("UE", "Union européenne"),
                            ("HORS_UE", "Hors Union européenne"),
                        ],
                        max_length=8,
                    ),
                ),
                (
                    "nud",
                    models.CharField(
                        blank=True,
                        max_length=30,
                        verbose_name="Numéro unique d'enregistrement",
                    ),
                ),
                ("telephone", models.CharField(blank=True, max_length=20)),
                ("telephone_portable", models.CharField(blank=True, max_length=20)),
                ("email", models.CharField(blank=True, max_length=120)),
                ("adresse_numero", models.CharField(blank=True, max_length=10)),
                ("adresse_voie", models.CharField(blank=True, max_length=150)),
                ("adresse_complement", models.CharField(blank=True, max_length=150)),
                ("code_postal", models.CharField(blank=True, max_length=5)),
                ("commune", models.CharField(blank=True, max_length=100)),
                (
                    "logement",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PROPRIETAIRE", "Propriétaire occupant"),
                            ("SOCIAL", "Locataire d'un logement social"),
                            (
                                "PRIVE",
                                "Locataire ou sous-locataire d'un logement privé",
                            ),
                            ("AUTRE", "Autre"),
                        ],
                        max_length=12,
                    ),
                ),
                ("logement_autre", models.CharField(blank=True, max_length=150)),
                (
                    "bailleur",
                    models.CharField(
                        blank=True,
                        max_length=150,
                        verbose_name="Nom du bailleur figurant sur la quittance",
                    ),
                ),
                ("numero_allocataire", models.CharField(blank=True, max_length=20)),
                (
                    "personnes",
                    models.TextField(
                        blank=True,
                        help_text="Une par ligne : Nom;Prénom;JJ/MM/AAAA;Lien de parenté",
                        verbose_name="Personnes à loger en plus de vous-même",
                    ),
                ),
                (
                    "situations",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Codes des situations cochées (8.1 à 8.9)",
                    ),
                ),
                (
                    "nature_local",
                    models.CharField(
                        blank=True, max_length=120, verbose_name="8.1 Nature du local"
                    ),
                ),
                (
                    "hebergeurs",
                    models.TextField(
                        blank=True,
                        verbose_name="8.2 Personnes qui vous hébergent (nom, adresse, depuis quand)",
                    ),
                ),
                (
                    "hebergement_nb_personnes",
                    models.CharField(
                        blank=True,
                        max_length=10,
                        verbose_name="8.2 Nombre de personnes dans le logement",
                    ),
                ),
                (
                    "hebergement_surface",
                    models.CharField(
                        blank=True, max_length=10, verbose_name="8.2 Surface (m²)"
                    ),
                ),
                (
                    "hebergement_pieces",
                    models.CharField(
                        blank=True, max_length=10, verbose_name="8.2 Nombre de pièces"
                    ),
                ),
                (
                    "structure_nom",
                    models.CharField(
                        blank=True,
                        max_length=150,
                        verbose_name="8.4 Nom de la structure",
                    ),
                ),
                (
                    "structure_date",
                    models.CharField(
                        blank=True,
                        max_length=10,
                        verbose_name="8.4 Date d'entrée dans la structure",
                    ),
                ),
                (
                    "surface_totale",
                    models.CharField(
                        blank=True,
                        max_length=10,
                        verbose_name="8.8 Surface totale (m²)",
                    ),
                ),
                (
                    "nombre_pieces",
                    models.CharField(
                        blank=True, max_length=10, verbose_name="8.8 Nombre de pièces"
                    ),
                ),
                (
                    "assistant_nom",
                    models.CharField(
                        blank=True,
                        max_length=120,
                        verbose_name="10.1.1 Nom de la personne qui vous assiste",
                    ),
                ),
                (
                    "assistant_organisme",
                    models.CharField(
                        blank=True,
                        max_length=150,
                        verbose_name="10.1.1 Nom de son organisme",
                    ),
                ),
                (
                    "assistant_adresse_numero",
                    models.CharField(blank=True, max_length=10),
                ),
                (
                    "assistant_adresse_voie",
                    models.CharField(blank=True, max_length=150),
                ),
                ("assistant_code_postal", models.CharField(blank=True, max_length=5)),
                ("assistant_commune", models.CharField(blank=True, max_length=100)),
                ("assistant_telephone", models.CharField(blank=True, max_length=20)),
                (
                    "argumentaire",
                    models.TextField(blank=True, verbose_name="11. Argumentaire libre"),
                ),
                ("date_modification", models.DateTimeField(auto_now=True)),
                (
                    "beneficiaire",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recours_dalo",
                        to="beneficiaire.beneficiaire",
                    ),
                ),
                (
                    "modifie_par",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recours_dalo_modifies",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Recours DALO (Cerfa 15036)",
                "verbose_name_plural": "Recours DALO (Cerfa 15036)",
            },
        ),
    ]
