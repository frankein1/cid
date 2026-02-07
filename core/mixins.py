# core/mixins.py

from django.db import models
from django.conf import settings

class TimestampedMixin(models.Model):
    """
    Mixin pour ajouter automatiquement les dates de création et modification
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    class Meta:
        abstract = True


class AuditedMixin(TimestampedMixin):
    """
    Mixin complet pour audit : ajoute timestamps et qui a créé/modifié
    """
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_crees',
        verbose_name="Créé par"
    )
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_modifies',
        verbose_name="Modifié par"
    )

    class Meta:
        abstract = True
