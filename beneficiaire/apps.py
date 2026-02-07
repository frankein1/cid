# beneficiaire/apps.py

from django.apps import AppConfig

class BeneficiaireConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'beneficiaire'
    verbose_name = 'Gestion des Bénéficiaires'
