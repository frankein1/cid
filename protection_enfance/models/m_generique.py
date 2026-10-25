# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/models/m_generique.py
"""
Socle commun du module protection de l'enfance (IP aujourd'hui, ASE demain) :
numérotation départementale D13 et journal des actions.
Repris de l'embryon (NumeroCounter, generate_numero, HistoriqueAction).
"""
from django.conf import settings
from django.db import models, transaction


class NumeroCounter(models.Model):
    """Compteur pour générer des numéros D13-00000001 de façon atomique."""
    prefix = models.CharField(max_length=10, unique=True, default='D13')
    last_value = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.prefix}-{self.last_value}"


def generate_numero(prefix='D13'):
    """Génère atomiquement un numéro D13-xxxxxxxx (jamais deux fois le même)."""
    with transaction.atomic():
        counter, _ = NumeroCounter.objects.select_for_update().get_or_create(prefix=prefix)
        counter.last_value += 1
        counter.save(update_fields=['last_value'])
        return f"{prefix}-{counter.last_value:08d}"


class HistoriqueAction(models.Model):
    """Journal de TOUT ce qui se passe sur une IP (traçabilité, prévention des vices de procédure)."""
    information = models.ForeignKey('protection_enfance.InformationPreoccupante',
                                    related_name='historique_actions', on_delete=models.CASCADE)
    action = models.CharField(max_length=200)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    commentaire = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-date', '-id')
        verbose_name = "Historique d'action"
        verbose_name_plural = "Historiques d'actions"

    def __str__(self):
        return f"{self.information.numero} - {self.action} - {self.date:%d/%m/%Y}"
