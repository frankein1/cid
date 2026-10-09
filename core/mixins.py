# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

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

    def save(self, *args, **kwargs):
        """
        Remplit automatiquement l'auteur à partir de l'utilisateur connecté
        (voir core/utilisateur_courant.py) :
        - cree_par    : à la création, s'il n'a pas été renseigné par la vue
        - modifie_par : à chaque enregistrement
        Sans utilisateur connecté (scripts init2, install...), rien ne change.
        """
        from core.utilisateur_courant import get_utilisateur_courant
        user = get_utilisateur_courant()
        if user is not None:
            if self._state.adding and not self.cree_par_id:
                self.cree_par = user
            self.modifie_par = user
            # save(update_fields=[...]) n'enregistre que les champs listés
            update_fields = kwargs.get('update_fields')
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'modifie_par', 'updated_at'}
        super().save(*args, **kwargs)
