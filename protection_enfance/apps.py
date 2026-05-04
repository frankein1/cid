# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/apps.py
from django.apps import AppConfig

class ProtectionEnfanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'protection_enfance'
    verbose_name = 'Protection de l\'Enfance'
    
    def ready(self):
        # Importer les signaux si nécessaire
        try:
            import protection_enfance.signals  # noqa
        except ImportError:
            pass
