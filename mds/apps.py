# mds/apps.py
from django.apps import AppConfig


class MaisonDptaleSolidariteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mds'
    verbose_name = "Maison Départementale des Solidarités"

    def ready(self):
        """
        Méthode exécutée au démarrage de Django.
        On y importe les permissions pour connecter le signal post_migrate.
        """
        import mds.permissions

class PlanningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'planning'
    verbose_name = 'Gestion du Planning'

    def ready(self):
        """
        Méthode appelée au démarrage de Django
        Charge les signaux définis dans signals.py
        """
        import planning.signals  # Import des signaux pour les activer
