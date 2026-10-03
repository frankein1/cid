# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# mds/apps.py
from django.apps import AppConfig


class MaisonDptaleSolidariteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mds'
    verbose_name = "Maison Départementale des Solidarités"
