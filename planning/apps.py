# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# planning/apps.py - VERSION CORRIGÉE SANS RUNTIMEWARNING

from django.apps import AppConfig

class PlanningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'planning'
    verbose_name = 'Planning et rendez-vous'
    
    def ready(self):
        """
        Initialisation de l'application.
        ✅ CORRIGÉ : Pas de requête SQL ici, uniquement l'import des signaux
        """
        # Import des signaux (sans requête SQL)
        try:
            import planning.signals
        except ImportError:
            pass
        
        # ✅ NOTE : L'initialisation de la configuration se fait maintenant via :
        # python manage.py shell
        # >>> from planning.init_planning_config import init_planning_config
        # >>> init_planning_config()
        #
        # Ou directement depuis une vue/admin après les migrations
