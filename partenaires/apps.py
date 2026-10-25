# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# partenaires/apps.py
from django.apps import AppConfig


class PartenairesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'partenaires'
    verbose_name = "Annuaire des partenaires"
