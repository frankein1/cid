# ged/apps.py
from django.apps import AppConfig

class GedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ged'

    def ready(self):
        import ged.signals
