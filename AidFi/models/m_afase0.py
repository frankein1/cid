# AidFi/models/afase.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.mixins import TimestampedMixin, AuditedMixin
from beneficiaire.models import Beneficiaire
from ged.models import DocumentGED


# ============================================================================
# DEMANDE AFASE (SOCLE)
# ============================================================================

class DemandeAFASE(AuditedMixin):
    """
    Demande d’Aide Financière ASE (AFASE)
    """

    STATUT_CHOICES = [
        ("BROUILLON", "Brouillon"),
        ("DEPOSE", "Déposée"),
        ("DECIDE", "Décidée"),
    ]

    AVIS_TS_CHOICES = [
        ("FAVORABLE", "Favorable"),
        ("DEFAVORABLE", "Défavorable"),
    ]

    beneficiaire = models.ForeignKey(
        Beneficiaire,
        on_delete=models.PROTECT,
        related_name="demandes_afase"
    )

    numero_genesis = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="N° GENESIS"
    )

    premiere_demande = models.BooleanField(
        default=True,
        verbose_name="Première demande"
    )

    statut = models.CharField(
        max_length=10,
        choices=STATUT_CHOICES,
        default="BROUILLON"
    )

    date_depot = models.DateTimeField(
        null=True,
        blank=True
    )

    date_decision = models.DateTimeField(
        null=True,
        blank=True
    )

    # --- Proposition AFASE ---
    avis_ts = models.CharField(
        max_length=15,
        choices=AVIS_TS_CHOICES,
        verbose_name="Avis du travailleur social"
    )

    montant_demande = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Montant demandé"
    )

    duree_demande = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Durée demandée (mois)"
    )

    class Meta:
        verbose_name = "Demande AFASE"
        verbose_name_plural = "Demandes AFASE"
        ordering = ["-created_at"]

    def __str__(self):
        return f"AFASE {self.id} – {self.beneficiaire}"

    def deposer(self):
        if self.statut != "BROUILLON":
            raise ValidationError("Seule une demande en brouillon peut être déposée.")
        self.statut = "DEPOSE"
        self.date_depot = timezone.now()
        self.save(update_fields=["statut", "date_depot"])

    def decider(self):
        if self.statut != "DEPOSE":
            raise ValidationError("La décision n’est possible que sur une demande déposée.")
        self.statut = "DECIDE"
        self.date_decision = timezone.now()
        self.save(update_fields=["statut", "date_decision"])


# ============================================================================
# EVALUATION SOCIALE
# ============================================================================

class EvaluationSocialeAFASE(AuditedMixin):
    demande = models.OneToOneField(
        DemandeAFASE,
        on_delete=models.CASCADE,
        related_name="evaluation_sociale"
    )

    situation_sociale = models.TextField()
    analyse_problematique = models.TextField()
    justification_demande = models.TextField(
        verbose_name="Justification de la demande"
    )

    commentaire_familial = models.TextField(
        blank=True
    )

    class Meta:
        verbose_name = "Évaluation sociale AFASE"
        verbose_name_plural = "Évaluations sociales AFASE"


# ============================================================================
# BUDGET AFASE
# ============================================================================

class BudgetAFASE(AuditedMixin):
    demande = models.OneToOneField(
        DemandeAFASE,
        on_delete=models.CASCADE,
        related_name="budget"
    )

    ressources = models.JSONField()
    charges = models.JSONField()

    nb_personnes_foyer = models.PositiveSmallIntegerField(
        editable=False
    )

    reste_a_vivre = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        editable=False
    )

    class Meta:
        verbose_name = "Budget AFASE"
        verbose_name_plural = "Budgets AFASE"

    def save(self, *args, **kwargs):
        # Calcul du nombre de personnes au foyer
        beneficiaire = self.demande.beneficiaire
        self.nb_personnes_foyer = (
            1
            + (1 if beneficiaire.conjoint else 0)
            + beneficiaire.enfants.count()
        )

        total_ressources = sum(self.ressources.values())
        total_charges = sum(self.charges.values())

        if self.nb_personnes_foyer > 0:
            self.reste_a_vivre = (
                total_ressources - total_charges
            ) / self.nb_personnes_foyer
        else:
            self.reste_a_vivre = 0

        super().save(*args, **kwargs)


# ============================================================================
# DECISION AFASE
# ============================================================================

class DecisionAFASE(AuditedMixin):

    TYPE_DECISION_CHOICES = [
        ("ACCORD", "Accord"),
        ("REFUS", "Refus"),
    ]

    demande = models.OneToOneField(
        DemandeAFASE,
        on_delete=models.CASCADE,
        related_name="decision"
    )

    type_decision = models.CharField(
        max_length=10,
        choices=TYPE_DECISION_CHOICES
    )

    code_decision = models.CharField(
        max_length=20,
        verbose_name="Code décision"
    )

    montant_accorde = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    duree_accordee = models.PositiveSmallIntegerField()

    motivation = models.TextField(
        blank=True
    )

    class Meta:
        verbose_name = "Décision AFASE"
        verbose_name_plural = "Décisions AFASE"

    def clean(self):
        if self.type_decision == "REFUS" and not self.motivation:
            raise ValidationError(
                {"motivation": "La motivation est obligatoire en cas de refus."}
            )
