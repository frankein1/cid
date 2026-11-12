# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/apps.py
from django.apps import AppConfig


class RelationUsagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ru"
    verbose_name = "Relation Usager (RU)"
