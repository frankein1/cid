# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# adultevul/apps.py
from django.apps import AppConfig


class AdulteVulnerableConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "adultevul"
    verbose_name = "Adultes vulnérables (information préoccupante majeur)"
