# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# ged/apps.py
from django.apps import AppConfig

class GedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ged'

    def ready(self):
        import ged.signals
