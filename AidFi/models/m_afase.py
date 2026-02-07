# AidFi/models/m_afase.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from .m_generique import DemandeAide
from core.mixins import AuditedMixin

# --- CODES INSTRUCTION (Agent Social) ---
CODES_INSTRUCTION_AFASE = {
    "1": "Droits en attente",
    "2": "Droits suspendus",
    "3": "Droits diminués",
    "4": "Difficulté budgétaire ponctuelle / crise familiale",
    "5": "Surendettement",
    "6": "Catastrophes naturelles / crise externe à la famille",
    "7": "Aucun droit en attente et sans revenus connus",
}

# --- CODES DÉCISION ---
ACCORD_AFASE_CHOICES = {
    "1": "Soutien alimentaire",
    "2": "Modes de garde",
    "3": "Colonies",
    "4": "Scolarité / vêture",
    "5": "Cantine",
    "6": "Activités",
    "7": "Santé",
    "8": "Logement",
    "9": "Équipement",
    "10": "Crise familiale",
    "12": "Transport",
    "13": "Catastrophes",
}

REFUS_AFASE_CHOICES = {
    "1": "Absence de justificatifs",
    "2": "Ressources suffisantes",
    "3": "Autre dispositif",
    "4": "Motif non recevable",
    "5": "Absence d’adhésion",
    "6": "Droits rétablis",
    "7": "Aide déjà versée",
    "8": "Récurrence",
}

# ============================================================================
# DEMANDE AFASE
# ============================================================================

class DemandeAFASE(DemandeAide):
    """
    Demande AFASE
    Alignée sur le cycle de vie générique DemandeAide
    """

    numero_genesis = models.CharField(max_length=50, blank=True)
    premiere_demande = models.BooleanField(default=True)
    duree_demande = models.PositiveSmallIntegerField(default=1)

    AVIS_TS_CHOICES = [
        ("FAVORABLE", "Favorable"),
        ("DEFAVORABLE", "Défavorable"),
    ]
    avis_ts = models.CharField(max_length=15, choices=AVIS_TS_CHOICES)

    class Meta:
        verbose_name = "Demande AFASE"
        verbose_name_plural = "Demandes AFASE"
        db_table = "AidFi_demandeafase"

    # --- MÉTHODES MÉTIER ---

    def deposer(self):
        if self.statut != "BROUILLON":
            raise ValidationError("Seule une demande en brouillon peut être déposée.")
        self.statut = "DEPOSEE"
        self.save(update_fields=["statut"])

    def passer_en_instruction(self):
        if self.statut != "DEPOSEE":
            raise ValidationError("Instruction impossible.")
        self.statut = "EN_INSTRUCTION"
        self.save(update_fields=["statut"])
    
    def verrouiller(self):
        self.statut = "VALIDEE"
        self.est_verrouillee = True
        self.save(update_fields=["statut", "est_verrouillee"])
        
    def ajourner(self):
        self.statut = "BROUILLON"
        self.save(update_fields=["statut"])

    def accorder(self):
        self.statut = "ACCORDEE"
        self.save(update_fields=["statut"])

    def refuser(self):
        self.statut = "REFUSEE"
        self.save(update_fields=["statut"])


# ============================================================================
# ÉVALUATION SOCIALE
# ============================================================================

class EvaluationSocialeAFASE(AuditedMixin):
    demande = models.OneToOneField(
        DemandeAFASE,
        on_delete=models.CASCADE,
        related_name="evaluation_afase"
    )
    code_instruction = models.CharField(
        max_length=2,
        choices=[(k, v) for k, v in CODES_INSTRUCTION_AFASE.items()],
        blank=True
    )
    situation_sociale = models.TextField()
    analyse_problematique = models.TextField()
    justification_demande = models.TextField()
    commentaire_familial = models.TextField(blank=True)

    @property
    def libelle_instruction(self):
        return CODES_INSTRUCTION_AFASE.get(self.code_instruction, "Non renseigné")


# ============================================================================
# BUDGET
# ============================================================================

class BudgetAFASE(AuditedMixin):
    demande = models.OneToOneField(
        DemandeAFASE,
        on_delete=models.CASCADE,
        related_name="budget"
    )

    ressources = models.JSONField(default=dict)
    charges = models.JSONField(default=dict)

    nb_personnes_foyer = models.PositiveSmallIntegerField(editable=False)
    reste_a_vivre = models.DecimalField(max_digits=8, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        beneficiaire = self.demande.beneficiaire
        self.nb_personnes_foyer = 1 + beneficiaire.enfants.count()
        total_ressources = sum(self.ressources.values())
        total_charges = sum(self.charges.values())
        self.reste_a_vivre = (
            (total_ressources - total_charges) / self.nb_personnes_foyer
            if self.nb_personnes_foyer else 0
        )
        super().save(*args, **kwargs)


# ============================================================================
# DÉCISION
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
    type_decision = models.CharField(max_length=10, choices=TYPE_DECISION_CHOICES)
    code_decision = models.CharField(max_length=2)
    montant_accorde = models.DecimalField(max_digits=8, decimal_places=2)
    duree_accordee = models.PositiveSmallIntegerField()
    motivation = models.TextField(blank=True)

    def clean(self):
        if self.type_decision == "REFUS" and not self.motivation:
            raise ValidationError("Motivation obligatoire en cas de refus.")

    @property
    def libelle_decision(self):
        if self.type_decision == "ACCORD":
            return ACCORD_AFASE_CHOICES.get(self.code_decision, "Accord inconnu")
        return REFUS_AFASE_CHOICES.get(self.code_decision, "Refus inconnu")
