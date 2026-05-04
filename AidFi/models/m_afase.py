# AidFi/models/m_afase.py

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from AidFi.models.m_generique import DemandeAide
from core.mixins import AuditedMixin
from beneficiaire.models import LienFamilial


# ==========================================================
# CODES MÉTIER
# ==========================================================

CODES_INSTRUCTION_AFASE = {
    "1": "Droits en attente",
    "2": "Droits suspendus",
    "3": "Droits diminués",
    "4": "Difficulté budgétaire ponctuelle / crise familiale",
    "5": "Surendettement",
    "6": "Catastrophes naturelles / crise externe à la famille",
    "7": "Aucun droit en attente et sans revenus connus",
}

# ✅ CORRIGÉ : Listes de tuples au lieu de dictionnaires
ACCORD_AFASE_CHOICES = [
    ("1", "Soutien alimentaire"),
    ("2", "Modes de garde"),
    ("3", "Colonies"),
    ("4", "Scolarité / vêture"),
    ("5", "Cantine"),
    ("6", "Activités"),
    ("7", "Santé"),
    ("8", "Logement"),
    ("9", "Équipement"),
    ("10", "Crise familiale"),
    ("12", "Transport"),
    ("13", "Catastrophes"),
]

REFUS_AFASE_CHOICES = [
    ("1", "Absence de justificatifs"),
    ("2", "Ressources suffisantes"),
    ("3", "Autre dispositif"),
    ("4", "Motif non recevable"),
    ("5", "Absence d'adhésion"),
    ("6", "Droits rétablis"),
    ("7", "Aide déjà versée"),
    ("8", "Récurrence"),
]


# ==========================================================
# DEMANDE AFASE
# ==========================================================

class DemandeAFASE(DemandeAide):
    """
    Demande AFASE – extension métier de DemandeAide
    La décision devient définitive après verrouillage.
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

    def __str__(self):
        return f"AFASE-{self.id} – {self.beneficiaire.nom}"

    # ------------------------------
    # VERROU MÉTIER (CLÉ DU SYSTÈME)
    # ------------------------------

    def verrouiller(self):
        """
        Verrouille définitivement la demande après décision cadre.
        Toute modification ultérieure est interdite.
        """
        self.statut = "VERROUILLEE"
        self.save(update_fields=["statut"])

    @property
    def est_verrouillee(self):
        return self.statut == "VERROUILLEE"

    @property
    def est_modifiable(self):
        """
        Une demande verrouillée ne peut plus être modifiée
        par aucun acteur (TS ou cadre).
        """
        return not self.est_verrouillee

    # ------------------------------
    # ACCÈS MÉTIER SIMPLIFIÉS
    # ------------------------------

    @property
    def code_demande(self):
        """
        Code de contexte renseigné par le travailleur social
        """
        if hasattr(self, "evaluation_afase"):
            return self.evaluation_afase.code_instruction
        return None

    @property
    def libelle_demande(self):
        if self.code_demande:
            return CODES_INSTRUCTION_AFASE.get(self.code_demande, "Code inconnu")
        return "Non renseigné"

# ==========================================================
# ÉVALUATION SOCIALE (AUDITÉE - NON VERROUILLÉE SEULE)
# ==========================================================

class EvaluationSocialeAFASE(AuditedMixin):
    demande = models.OneToOneField(
        DemandeAFASE,
        on_delete=models.CASCADE,
        related_name="evaluation_afase",
    )

    code_instruction = models.CharField(
        max_length=2,
        choices=[(k, v) for k, v in CODES_INSTRUCTION_AFASE.items()],
        blank=True,
        verbose_name="Code de demande AFASE",
    )

    situation_sociale = models.TextField(blank=True)
    analyse_problematique = models.TextField(blank=True)
    justification_demande = models.TextField()
    commentaire_familial = models.TextField(blank=True)

    class Meta:
        verbose_name = "Évaluation sociale AFASE"
        verbose_name_plural = "Évaluations sociales AFASE"

    def __str__(self):
        return f"Évaluation AFASE – demande {self.demande.id}"


# ==========================================================
# BUDGET
# ==========================================================

class BudgetAFASE(AuditedMixin):
    demande = models.OneToOneField(
        DemandeAFASE,
        on_delete=models.CASCADE,
        related_name="budget",
    )

    ressources = models.JSONField(default=dict)
    charges = models.JSONField(default=dict)

    nb_personnes_foyer = models.PositiveSmallIntegerField(
        default=1, editable=False
    )
    reste_a_vivre = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, editable=False
    )

    class Meta:
        verbose_name = "Budget AFASE"
        verbose_name_plural = "Budgets AFASE"

    def __str__(self):
        return f"Budget AFASE – demande {self.demande.id}"

    def save(self, *args, **kwargs):
        beneficiaire = self.demande.beneficiaire

        # Calcul du nombre de personnes au foyer
        nb = 1
        liens = (
            LienFamilial.objects.filter(personne_a=beneficiaire)
            | LienFamilial.objects.filter(personne_b=beneficiaire)
        )

        for lien in liens:
            if lien.vit_au_foyer:
                nb += 1

        self.nb_personnes_foyer = max(nb, 1)

        # Calcul du reste à vivre
        total_ressources = sum(
            float(v) for v in (self.ressources or {}).values() if v
        )
        total_charges = sum(
            float(v) for v in (self.charges or {}).values() if v
        )

        solde_mensuel = total_ressources - total_charges
        self.reste_a_vivre = round(
            max(solde_mensuel / self.nb_personnes_foyer / 30, 0), 2
        )

        super().save(*args, **kwargs)


# ==========================================================
# DÉCISION (AUDITÉE + BLOQUÉE PAR LA DEMANDE)
# ==========================================================

class DecisionAFASE(AuditedMixin):
    TYPE_DECISION_CHOICES = [
        ("ACCORD", "Accord"),
        ("REFUS", "Refus"),
        ("AJO", "Ajournement"),
    ]

    demande = models.OneToOneField(
        DemandeAFASE,
        on_delete=models.CASCADE,
        related_name="decision",
    )

    type_decision = models.CharField(
        max_length=10, choices=TYPE_DECISION_CHOICES
    )
    code_decision = models.CharField(max_length=2, blank=True)

    montant_accorde = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    duree_accordee = models.PositiveSmallIntegerField(default=1)
    motivation = models.TextField(blank=True)

    date_decision = models.DateTimeField(default=timezone.now)
    decide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="decisions_afase",
    )

    class Meta:
        verbose_name = "Décision AFASE"
        verbose_name_plural = "Décisions AFASE"

    def __str__(self):
        return f"Décision AFASE – demande {self.demande.id}"

    def clean(self):
        if self.type_decision == "REFUS" and not self.motivation:
            raise ValidationError(
                "Motivation obligatoire en cas de refus."
            )

    @property
    def libelle_decision(self):
        if self.type_decision == "ACCORD":
            return dict(ACCORD_AFASE_CHOICES).get(
                self.code_decision, "Accord non précisé"
            )
        if self.type_decision == "REFUS":
            return dict(REFUS_AFASE_CHOICES).get(
                self.code_decision, "Refus non précisé"
            )
        return "Ajournement"
