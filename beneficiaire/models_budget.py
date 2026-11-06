# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/models_budget.py
"""Budget du foyer : établi sur la fiche d'un usager, daté, historisé (un nouveau budget ne remplace pas l'ancien).
Mêmes rubriques que le budget de la demande d'AFASE (AidFi/services/budget_afase.py), pour passer de l'un à l'autre
sans ressaisie."""
from decimal import Decimal

from django.db import models
from django.utils import timezone

from core.mixins import AuditedMixin


class BudgetFoyer(AuditedMixin):
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE, related_name='budgets_foyer')
    date_etabli = models.DateField("Établi le", default=timezone.localdate)
    ressources = models.JSONField(default=dict)
    charges = models.JSONField(default=dict)
    dettes = models.JSONField(default=list, blank=True)
    nb_personnes_foyer = models.PositiveSmallIntegerField("Nombre de personnes vivant au foyer", default=1)
    reste_a_vivre = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    commentaire = models.TextField("Observations", blank=True,
                                   help_text="Éléments utiles à la lecture du budget (ressources fluctuantes, dette en "
                                             "cours de plan, etc.). Pas d'appréciation sur la personne.")

    class Meta:
        verbose_name = "Budget du foyer"
        verbose_name_plural = "Budgets du foyer"
        ordering = ['-date_etabli', '-pk']

    def __str__(self):
        return f"Budget du foyer de {self.beneficiaire} au {self.date_etabli:%d/%m/%Y}"

    def save(self, *args, **kwargs):
        from AidFi.services.budget_afase import totaux
        self.reste_a_vivre = totaux(self.ressources, self.charges, self.nb_personnes_foyer)['reste_a_vivre']
        super().save(*args, **kwargs)

    @property
    def totaux(self):
        from AidFi.services.budget_afase import totaux
        return totaux(self.ressources, self.charges, self.nb_personnes_foyer)

    @property
    def affichage(self):
        from AidFi.services.budget_afase import lignes_affichage
        return lignes_affichage(self.ressources, self.charges)

    @property
    def total_dettes(self):
        from AidFi.services.budget_afase import _d
        return sum((_d(d.get('montant')) for d in (self.dettes or [])), Decimal(0))
