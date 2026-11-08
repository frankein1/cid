# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/migrations/0008_durees_conservation.py

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_identite_proconnect"),
    ]

    operations = [
        migrations.CreateModel(
            name="DureeConservation",
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
                    "code",
                    models.CharField(
                        max_length=40, unique=True, verbose_name="Traitement"
                    ),
                ),
                (
                    "base_active_mois",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="Base active (mois)"
                    ),
                ),
                (
                    "point_de_depart",
                    models.CharField(
                        blank=True, max_length=200, verbose_name="Point de départ"
                    ),
                ),
                (
                    "archivage_mois",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Archivage intermédiaire (mois)",
                    ),
                ),
                (
                    "sort_final",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("SUPPRESSION", "Suppression"),
                            ("ANONYMISATION", "Anonymisation"),
                            ("ARCHIVES", "Versement aux archives départementales"),
                        ],
                        max_length=15,
                        verbose_name="Sort final",
                    ),
                ),
                (
                    "reference",
                    models.TextField(
                        blank=True, verbose_name="Base légale ou référence"
                    ),
                ),
                (
                    "commentaire",
                    models.TextField(blank=True, verbose_name="Commentaire du DPO"),
                ),
                (
                    "importe_le",
                    models.DateTimeField(auto_now=True, verbose_name="Importé le"),
                ),
                (
                    "importe_par",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Importé par",
                    ),
                ),
            ],
            options={
                "verbose_name": "Durée de conservation (RGPD)",
                "verbose_name_plural": "Durées de conservation (RGPD)",
                "ordering": ["code"],
            },
        ),
    ]
