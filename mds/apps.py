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
        # Import différé pour éviter les cycles
        from mds.permissions import create_mds_permissions
        from django.db.models.signals import post_migrate
        
        # Connexion explicite du signal
        post_migrate.connect(create_mds_permissions, sender=self)


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
