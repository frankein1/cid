# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/apps.py
from django.apps import AppConfig


class ConnecteursConfig(AppConfig):
    """Liens avec les services de l'État (API Particulier, plus tard ProConnect…)."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'connecteurs'
    verbose_name = "Connecteurs externes"
