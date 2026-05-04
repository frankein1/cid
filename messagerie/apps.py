# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# messagerie/apps.py

from django.apps import AppConfig

class MessagerieConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messagerie'
    verbose_name = "Messagerie interne"
