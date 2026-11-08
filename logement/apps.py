# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/apps.py
from django.apps import AppConfig


class LogementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logement'
    verbose_name = 'Logement'
