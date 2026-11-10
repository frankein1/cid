# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0011_merge_hebergement_asell.py
"""Fusion des deux migrations 0010 (rappels de l'hébergement et ASELL), toutes deux issues de 0009_hebergement_urgence."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("logement", "0010_hebergement_rappels"),
        ("logement", "0010_orientation_asell"),
    ]

    operations = []
