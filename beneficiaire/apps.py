# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# beneficiaire/apps.py

from django.apps import AppConfig

class BeneficiaireConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'beneficiaire'
    verbose_name = 'Gestion des Bénéficiaires'
