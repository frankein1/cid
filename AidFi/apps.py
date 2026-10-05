# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/apps.py

from django.apps import AppConfig


class AidFiConfig(AppConfig):
    name = 'AidFi'
    verbose_name = "Aides financières"

    def ready(self):
        # Sans cette ligne, AidFi/signals.py n'est jamais chargé :
        # le suivi des statuts ne s'enregistrerait pas.
        from . import signals  # noqa: F401
