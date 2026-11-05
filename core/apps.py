# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# /core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core - Fondation du système'

    def ready(self):
        # On réactive l'importation des signaux
        import core.signals
        # Journal d'activité : créations, modifications, suppressions, déconnexions
        from django.contrib.auth.signals import user_logged_in, user_logged_out
        from core import journal
        journal.brancher_signaux()
        user_logged_in.connect(journal.connexion, dispatch_uid="journal-connexion")
        user_logged_out.connect(journal.deconnexion, dispatch_uid="journal-deconnexion")
