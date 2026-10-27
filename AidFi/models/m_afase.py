# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

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
# NB (annexe 4) : les codes 4 et 7 ne peuvent pas être inversés, pour des raisons statistiques.

# Codification des aides financières ASE (annexe 4 de la note de service)
ACCORD_AFASE_CHOICES = [
    ("1", "Soutien alimentaire"),
    ("2", "Modes de garde (CLSH, crèche…)"),
    ("3", "Participation aux frais de colonies"),
    ("4", "Scolarité, périscolarité, vêture"),
    ("5", "Frais de cantine"),
    ("6", "Activités sportives ou culturelles"),
    ("7", "Santé (mutuelle, soins enfants)"),
    ("8", "Logement (loyers, fluides, charges exceptionnelles, assurance habitation)"),
    ("9", "Équipement mobilier (électroménager, literie)"),
    ("10", "Soutien budgétaire / crise familiale"),
    # Code 11 « habillement » supprimé : englobé au code 4
    ("12", "Transport"),
    ("13", "Catastrophes naturelles / crise externe à la famille"),
]

REFUS_AFASE_CHOICES = [
    ("1", "Absence de justificatifs permettant d'évaluer les ressources et les charges"),
    ("2", "Ressources suffisantes"),
    ("3", "La demande relève d'un autre dispositif"),
    ("4", "Motif non lié aux besoins élémentaires de l'enfant"),
    ("5", "Absence d'adhésion de l'usager au projet défini avec le travailleur social"),
    ("6", "Droits rétablis et versés"),
    ("7", "Aide déjà versée"),
    ("8", "Récurrence des aides / maintien de revenu"),
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

    # Formulaire de demande (annexe 1 de la note de service)
    LIENS_DEMANDEUR = [
        ("MERE", "Mère"), ("PERE", "Père"), ("TUTEUR", "Tuteur"),
        ("CHARGE_EFFECTIVE", "Personne qui assume la charge effective de l'enfant"),
        ("FEMME_ENCEINTE", "Femme enceinte"), ("MINEUR_EMANCIPE", "Mineur émancipé"),
        ("JEUNE_MAJEUR", "Jeune majeur de moins de 21 ans"),
    ]
    QUALITES_TS = [
        ("AS", "Assistant(e) social(e)"), ("ES", "Éducateur(trice) spécialisé(e)"),
        ("CESF", "Conseiller(e) en économie sociale et familiale"), ("EJE", "Éducateur(trice) de jeunes enfants"),
    ]
    lien_demandeur = models.CharField("Lien du demandeur avec l'enfant", max_length=20, choices=LIENS_DEMANDEUR,
                                      blank=True)
    date_signature_demandeur = models.DateField(
        "Date de signature du demandeur", null=True, blank=True,
        help_text="Indispensable : le délai de traitement de 2 mois court à partir de cette date.")
    allocataire_caf = models.BooleanField("Allocataire CAF", null=True, blank=True)
    situation_pro_demandeur = models.CharField("Situation professionnelle du demandeur", max_length=200, blank=True)
    situation_pro_conjoint = models.CharField("Âge et situation professionnelle du conjoint", max_length=200,
                                              blank=True)
    historique_aides = models.TextField("Historique des aides ASE des 12 derniers mois", blank=True,
                                        help_text="Dates, décisions, montants (les AFASE de CID sont reprises).")
    autres_aides_sollicitees = models.TextField("Autres aides sollicitées", blank=True,
                                                help_text="Dates, organismes, décisions, montants.")
    qualite_ts = models.CharField("Qualité du travailleur social", max_length=5, choices=QUALITES_TS, blank=True)

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
        Modifiable seulement avant décision (brouillon, instruction, ajournement)
        et jamais une fois verrouillée.
        """
        return not self.est_verrouillee and super().est_modifiable

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
    # Éléments de contenu attendus (annexe 2 de la note de service)
    ADHESIONS = [("FORTE", "Forte"), ("PARTIELLE", "Partielle"), ("FAIBLE", "Faible"), ("AUCUNE", "Aucune")]
    plan_action = models.TextField("Plan d'action élaboré avec la famille", blank=True,
                                   help_text="En cohérence avec les autres dispositifs sollicités.")
    adhesion_famille = models.CharField("Degré d'adhésion de la famille au plan d'aide", max_length=10,
                                        choices=ADHESIONS, blank=True)
    affectation_aide = models.CharField("Affectation ciblée de l'aide", max_length=255, blank=True)
    parcours_insertion = models.TextField("Parcours d'insertion (jeunes de 16 à 21 ans sans scolarité ni stage)",
                                          blank=True)

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
    dettes = models.JSONField(default=list, blank=True)

    nb_personnes_foyer = models.PositiveSmallIntegerField("Nombre de personnes vivant au foyer", default=1)
    reste_a_vivre = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, editable=False
    )

    class Meta:
        verbose_name = "Budget AFASE"
        verbose_name_plural = "Budgets AFASE"

    def __str__(self):
        return f"Budget AFASE – demande {self.demande.id}"

    def save(self, *args, **kwargs):
        """
        Reste à vivre = (ressources − charges PAYÉES) / personnes au foyer / 30 (formulaire de la note).
        Le nombre de personnes est celui saisi sur le formulaire (proposé d'après le réseau familial).
        """
        from AidFi.services.budget_afase import totaux
        if not self.nb_personnes_foyer:
            self.nb_personnes_foyer = nb_personnes_au_foyer(self.demande.beneficiaire)
        self.reste_a_vivre = max(totaux(self.ressources, self.charges, self.nb_personnes_foyer)['reste_a_vivre'], 0)
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
        return sum((_d(d.get('montant')) for d in (self.dettes or [])), 0)


def nb_personnes_au_foyer(beneficiaire):
    """Demandeur + personnes liées qui vivent au foyer (proposition, modifiable sur le formulaire)."""
    nb = 1 + sum(1 for lien in (LienFamilial.objects.filter(personne_a=beneficiaire)
                                | LienFamilial.objects.filter(personne_b=beneficiaire)) if lien.vit_au_foyer)
    return max(nb, 1)


# ==========================================================
# ENFANTS CONCERNÉS (cadre A du formulaire)
# ==========================================================

class EnfantAFASE(models.Model):
    """
    Enfant mineur ou jeune majeur de moins de 21 ans, coché s'il est concerné par la demande.
    Enfant à naître : nom « XXX » et date d'accouchement prévue (règle de la note de service).
    """
    SEXES = [("F", "F"), ("M", "M")]
    demande = models.ForeignKey(DemandeAFASE, on_delete=models.CASCADE, related_name="enfants")
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='+')
    nom = models.CharField(max_length=60)
    prenom = models.CharField("Prénom", max_length=60, blank=True)
    date_naissance = models.DateField("Date de naissance (ou d'accouchement prévue)", null=True, blank=True)
    sexe = models.CharField(max_length=1, choices=SEXES, blank=True)
    situation = models.CharField("Situation (scolarité, formation, emploi…)", max_length=150, blank=True)
    a_naitre = models.BooleanField("Enfant à naître", default=False)
    concerne = models.BooleanField("Concerné par la demande", default=True)

    class Meta:
        ordering = ("date_naissance", "id")
        verbose_name = "Enfant (demande AFASE)"

    def __str__(self):
        return "Enfant à naître" if self.a_naitre else f"{self.prenom} {self.nom.upper()}"

    def save(self, *args, **kwargs):
        if self.a_naitre:
            self.nom, self.prenom = "XXX", ""
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

    # Circuit du paiement (après un accord) : cadre → service de contrôle → comptabilité → paierie
    PAIEMENT_A_CHOICES = [("FAMILLE", "La famille"), ("ORGANISME", "Un organisme (CLSH, colonie, cantine…)")]
    paiement_a = models.CharField("Paiement à", max_length=10, choices=PAIEMENT_A_CHOICES, blank=True)
    organisme_paiement = models.CharField("Organisme bénéficiaire du paiement", max_length=150, blank=True)
    date_transmission_controle = models.DateTimeField("Transmis au contrôle le", null=True, blank=True)
    transmis_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name="+")
    date_demande_paiement = models.DateField("Paiement demandé le", null=True, blank=True)
    reference_comptable = models.CharField("N° d'enregistrement comptable", max_length=60, blank=True)
    controle_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name="+")
    motif_renvoi = models.TextField("Motif du renvoi à la MDS", blank=True)
    # Ancien suivi manuel (conservé pour l'historique et les statistiques)
    date_envoi_regie = models.DateField("Envoyé à la régie le", null=True, blank=True)
    date_delivrance = models.DateField("Payé / délivré le", null=True, blank=True)
    montant_delivre = models.DecimalField("Montant délivré", max_digits=10, decimal_places=2,
                                          null=True, blank=True)

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
