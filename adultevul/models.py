# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# adultevul/models.py
"""
Information préoccupante concernant un adulte vulnérable (note MDS n°19, 10/01/2011).

Circuit : recueil (annexe 1) → qualification par le cadre → cellule d'évaluation (annexe 2)
→ investigations → rapport (propositions) → visa de l'adjoint Cohésion sociale → décision du directeur → clôture.
Les annexes 3 à 9 seront générées à partir de ces données (phases suivantes).
"""
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from protection_enfance.models.m_generique import generate_numero

DELAI_HUIT_JOURS = 8               # urgence : rapport sous 8 jours (annexe 2)
DELAI_DEUX_MOIS = 2                # rapport sous 2 mois (§ 3.3.4 et 3.3.5)

ORIGINES = [
    ('PERSONNE', 'La personne elle-même'),
    ('FAMILLE', 'Famille'),
    ('PARTICULIER', 'Particulier, voisinage'),
    ('INSTITUTION', 'Institution'),
    ('ANONYME', 'Anonyme'),
]
MODES_RECUEIL = [
    ('TELEPHONE', 'Appel téléphonique'),
    ('PRESENCE', 'Présence physique'),
    ('ECRIT', 'Par écrit'),
]
ELEMENTS = [
    ('CARENCE', 'Carence de soins'),
    ('MALT_PHYS', 'Maltraitance physique'),
    ('MALT_PSY', 'Maltraitance psychologique'),
    ('AUTRE', 'Autres'),
]
STATUTS = [
    ('RECUE', 'Recueillie, à qualifier'),
    ('NON_QUALIFIEE', 'Non qualifiée'),
    ('QUALIFIEE', 'Qualifiée, cellule à constituer'),
    ('EVALUATION', 'Cellule et investigations'),
    ('RAPPORT', 'Rapport soumis au visa'),
    ('VALIDEE', 'Rapport visé, décision à prendre'),
    ('DECIDEE', 'Décidée'),
    ('CLOTUREE', 'Clôturée'),
]
STATUTS_OUVERTS = ('RECUE', 'QUALIFIEE', 'EVALUATION', 'RAPPORT', 'VALIDEE', 'DECIDEE')
BADGES = {
    'RECUE': 'bg-gray-100 text-gray-800', 'NON_QUALIFIEE': 'bg-slate-100 text-slate-700',
    'QUALIFIEE': 'bg-amber-100 text-amber-800', 'EVALUATION': 'bg-blue-100 text-blue-800',
    'RAPPORT': 'bg-purple-100 text-purple-800', 'VALIDEE': 'bg-indigo-100 text-indigo-800',
    'DECIDEE': 'bg-teal-100 text-teal-800', 'CLOTUREE': 'bg-emerald-100 text-emerald-800',
}
PROPOSITIONS = [
    ('CLASSEMENT', 'Classement sans suite (annexe 4)'),
    ('POLICE', "Signalement à l'autorité judiciaire pour intervention des services de police (annexes 3 et 3 bis)"),
    ('ACCOMPAGNEMENT', 'Accompagnement social non contractualisé (annexe 5)'),
    ('MASP', 'Suivi contractualisé MASP niveau I ou II (annexe 6)'),
    ('PSYCHIATRIE', "Signalement au médecin chef de l'inter-secteur de psychiatrie (annexes 7 et 7 bis)"),
    ('ARS', "Signalement au médecin inspecteur de l'ARS (annexes 8 et 8 bis)"),
    ('PROTECTION_JURIDIQUE', 'Demande de protection juridique au procureur (annexes 9 et 9 bis)'),
]
URGENCES = [
    ('HUIT_JOURS', 'Urgente : rapport sous 8 jours'),
    ('DEUX_MOIS', 'Courante : rapport sous 2 mois'),
]
TRIBUNAUX = [
    ('AIX', 'TGI Aix-en-Provence (annexe 9.1)'),
    ('MARSEILLE', 'TGI Marseille (annexe 9.2)'),
    ('TARASCON', 'TGI Tarascon (fiche propre au parquet)'),
]
MESURES_PROTECTION = [
    ('TUTELLE', 'Tutelle'),
    ('CURATELLE', 'Curatelle'),
    ('SAUVEGARDE', 'Sauvegarde de justice'),
]
NIVEAUX_MASP = [
    ('I', 'Niveau I : sans perception des prestations sociales'),
    ('II', 'Niveau II : avec perception et gestion des prestations sociales'),
]
MODALITES = [
    ('VAD', 'Visite à domicile'),
    ('CONVOCATION', 'Convocation à la MDS'),
    ('AUTRE', 'Autre'),
]


class SituationAdulteVulnerable(models.Model):
    # --- recueil (annexe 1)
    numero = models.CharField(max_length=20, unique=True, db_index=True, editable=False)
    date_reception = models.DateField("Date de réception", default=timezone.localdate)
    recue_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name='av_recues', verbose_name="Agent ayant reçu l'information")
    mode_recueil = models.CharField("Mode de recueil", max_length=12, choices=MODES_RECUEIL, default='TELEPHONE')
    origine = models.CharField("Origine de l'information", max_length=16, choices=ORIGINES, default='PARTICULIER')
    institution = models.CharField("Institution (si origine institution)", max_length=200, blank=True)
    signalant_nom = models.CharField("Nom du signalant", max_length=150, blank=True)
    signalant_qualite = models.CharField("Qualité du signalant", max_length=150, blank=True)
    signalant_contact = models.TextField("Coordonnées du signalant", blank=True)
    signalant_connait_personne = models.BooleanField("Le signalant connaît la personne", default=False)
    signalant_confirmation_ecrite = models.BooleanField("Confirmation écrite demandée", default=False)
    intervenants_actuels = models.TextField(
        "Intervenants auprès de la personne (travailleurs sociaux, police, médecin traitant, psychiatrie…)",
        blank=True)
    elements = models.JSONField("Éléments de l'information", default=list, blank=True)
    danger_immediat = models.BooleanField("Danger immédiat", default=False)
    faits = models.TextField("Faits rapportés (mot pour mot)")
    evenement_declencheur = models.TextField("Événement qui a déclenché la transmission", blank=True)
    depuis_quand = models.CharField("Depuis quand les faits sont connus, répétition", max_length=200, blank=True)
    sante = models.TextField("Problème de santé", blank=True)
    conditions_vie = models.TextField("Conditions de vie, comportements", blank=True)

    # --- la personne
    personne_nom = models.CharField("Nom de la personne", max_length=150)
    personne_prenom = models.CharField("Prénom", max_length=150, blank=True)
    personne_naissance = models.DateField("Date de naissance", null=True, blank=True)
    personne_adresse = models.TextField("Adresse (lieu d'habitation ou d'hébergement)", blank=True)
    personne_hebergee = models.BooleanField("Hébergée (et non à domicile)", default=False)
    famille = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='situations_adultes_vulnerables',
                                verbose_name="Dossier de la personne dans CID")

    # --- MDS compétente et circuit
    mds = models.ForeignKey('mds.MDS', on_delete=models.PROTECT, null=True, blank=True,
                            related_name='situations_adultes_vulnerables', verbose_name="MDS compétente")
    statut = models.CharField(max_length=16, choices=STATUTS, default='RECUE')
    date_qualification = models.DateTimeField(null=True, blank=True)
    qualifiee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='av_qualifiees')
    motif_qualification = models.TextField(blank=True)

    # --- décision du directeur
    decision_commentaire = models.TextField("Décision administrative", blank=True)
    date_decision = models.DateTimeField(null=True, blank=True)
    decideur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='av_decidees')
    date_cloture = models.DateTimeField(null=True, blank=True)

    # --- protection juridique (annexes 9 et 9 bis)
    fiche = models.JSONField("Fiche de renseignements (saisie dans CID)", default=dict, blank=True)
    tribunal = models.CharField("Parquet compétent", max_length=12, choices=TRIBUNAUX, blank=True)
    mesure_protection = models.CharField("Mesure demandée", max_length=12, choices=MESURES_PROTECTION, blank=True)
    pj_acte_naissance = models.BooleanField("Pièce : acte de naissance ou justificatif d'état civil", default=False)
    pj_fiche = models.BooleanField("Pièce : fiche de renseignements complétée", default=False)
    pj_certificat = models.BooleanField("Pièce : certificat médical circonstancié (expert)", default=False)
    pj_certificat_absence = models.TextField(
        "Si le certificat ne peut pas être fourni : motif à expliquer au procureur", blank=True)

    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='av_creees')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-date_reception', '-id')
        verbose_name = "Information préoccupante – adulte vulnérable"
        verbose_name_plural = "Informations préoccupantes – adultes vulnérables"

    def __str__(self):
        return f"{self.numero} – {self.libelle_personne}"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = generate_numero('AV')
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('adultevul:detail', args=[self.pk])

    @property
    def libelle_personne(self):
        return f"{self.personne_nom.upper()} {self.personne_prenom}".strip()

    @property
    def badge(self):
        return BADGES.get(self.statut, 'bg-gray-100 text-gray-800')

    @property
    def est_ouverte(self):
        return self.statut in STATUTS_OUVERTS

    @property
    def date_limite_rapport(self):
        cellule = getattr(self, 'cellule', None)
        if not cellule or not cellule.date_cellule:
            return None
        if cellule.urgence == 'HUIT_JOURS':
            return cellule.date_cellule + timedelta(days=DELAI_HUIT_JOURS)
        return cellule.date_cellule + relativedelta(months=DELAI_DEUX_MOIS)

    @property
    def rapport_en_retard(self):
        limite = self.date_limite_rapport
        return bool(limite and self.est_ouverte and self.statut in ('EVALUATION', 'RAPPORT')
                    and timezone.localdate() > limite)


class CelluleEvaluation(models.Model):
    """Cellule d'évaluation (annexe 2). Verrouillée dès le visa du rapport."""
    situation = models.OneToOneField(SituationAdulteVulnerable, on_delete=models.CASCADE,
                                     related_name='cellule')
    date_cellule = models.DateField("Date de la cellule d'évaluation")
    urgence = models.CharField("Urgence", max_length=10, choices=URGENCES, default='DEUX_MOIS')
    participants = models.TextField(
        "Composition (nom, qualité)", blank=True,
        help_text="Adjoint Cohésion sociale, psychologue, médecin, travailleurs sociaux, partenaires…")
    referents = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='av_referent_de',
                                       verbose_name="Référent(s) de la situation")
    modalites = models.CharField("Modalités de la rencontre", max_length=12, choices=MODALITES, default='VAD')
    modalites_precision = models.CharField("Précision (autre modalité)", max_length=200, blank=True)
    investigations = models.TextField("Forme, nature et durée des investigations complémentaires", blank=True)
    plan_action = models.TextField("Plan d'action et calendrier", blank=True)
    propositions = models.JSONField("Propositions", default=list, blank=True)
    argumentation = models.TextField("Argumentation", blank=True)
    date_rapport = models.DateTimeField("Rapport soumis le", null=True, blank=True)

    def __str__(self):
        return f"Cellule {self.situation.numero} du {self.date_cellule:%d/%m/%Y}"

    @property
    def verrouillee(self):
        return self.situation.statut in ('RAPPORT', 'VALIDEE', 'DECIDEE', 'CLOTUREE')


class MesureMASP(models.Model):
    """Suivi d'un MASP (mesure d'accompagnement social personnalisé), géré dans CID (annexe 6)."""
    situation = models.OneToOneField(SituationAdulteVulnerable, on_delete=models.CASCADE, related_name='masp')
    niveau = models.CharField("Niveau", max_length=3, choices=NIVEAUX_MASP, default='I')
    date_demande = models.DateField("Date de la demande au SPM", null=True, blank=True)
    date_debut = models.DateField("Début de la mesure", null=True, blank=True)
    date_echeance = models.DateField("Échéance", null=True, blank=True)
    date_reevaluation = models.DateField("Réévaluation du plan d'action", null=True, blank=True)
    referent_nom = models.CharField("Nom du référent social", max_length=150, blank=True)
    referent_qualite = models.CharField("Qualité du référent", max_length=150, blank=True)
    notes = models.TextField("Suivi", blank=True)

    def __str__(self):
        return f"MASP {self.get_niveau_display()} – {self.situation.numero}"

    @property
    def prestations_gerees(self):
        return self.niveau == 'II'


class HistoriqueAV(models.Model):
    """Journal de tout ce qui se passe sur une situation (traçabilité des procédures)."""
    situation = models.ForeignKey(SituationAdulteVulnerable, on_delete=models.CASCADE,
                                  related_name='historique')
    date = models.DateTimeField(auto_now_add=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=60)
    detail = models.TextField(blank=True)

    class Meta:
        ordering = ('date', 'id')
