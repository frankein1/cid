# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0012_merge_dsf_hebergement.py
"""Fusion des feuilles DSF/ASELL (0011_merge_dsf_asell) et hébergement (0011_merge_hebergement_asell)."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("logement", "0011_merge_dsf_asell"),
        ("logement", "0011_merge_hebergement_asell"),
    ]

    operations = []
