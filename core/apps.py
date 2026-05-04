# /core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core - Fondation du système'

    def ready(self):
        # On réactive l'importation des signaux
        import core.signals
