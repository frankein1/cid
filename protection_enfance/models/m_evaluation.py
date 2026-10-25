# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/models/m_evaluation.py
"""
Évaluation d'une IP :
  - ActionIP   : chaque courrier, LRAR, appel, rendez-vous, audition, VAD, réunion… (dates, stats, preuve)
  - SaisineIP  : proposition du TS → décision du cadre → validation de l'inspecteur → saisine du procureur
  - RapportIP  : trame du rapport (reprise de l'ébauche d'enquête sociale de l'embryon), visas, avis de l'inspecteur
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from .m_ip import InformationPreoccupante

TYPES_ACTION = [
    ('REUNION_IP', "Réunion IP (présentation, choix du binôme)"),
    ('POINT_ETAPE', "Réunion de point d'étape"),
    ('REUNION_SYNTHESE', "Réunion de synthèse"),
    ('CONVOCATION', "Courrier de convocation"),
    ('LRAR', "Lettre recommandée avec accusé de réception"),
    ('APPEL', "Appel téléphonique"),
    ('MAIL', "Courriel"),
    ('RDV_MDS', "Rendez-vous en MDS"),
    ('AUDITION_ENFANT', "Audition d'un enfant (sans les parents)"),
    ('AUDITION_PARENTS', "Audition des parents"),
    ('VAD', "Visite à domicile"),
    ('PARTENAIRE', "Échange avec un partenaire"),
    ('AUTRE', "Autre"),
]
# Actions qui prennent place dans l'agenda (créneau du planning, domaine IP)
TYPES_AGENDA = {
    'REUNION_IP': 'REUNION', 'POINT_ETAPE': 'REUNION', 'REUNION_SYNTHESE': 'REUNION',
    'RDV_MDS': 'HORS_PERMANENCE', 'AUDITION_ENFANT': 'HORS_PERMANENCE', 'AUDITION_PARENTS': 'HORS_PERMANENCE',
    'VAD': 'VAD',
}
TYPES_COURRIER = ('CONVOCATION', 'LRAR')
RESULTATS = [
    ('PREVU', "Prévu"),
    ('REALISE', "Réalisé"),
    ('ABSENT', "Famille absente / porte close"),
    ('SANS_REPONSE', "Sans réponse"),
    ('ANNULE', "Annulé"),
    ('REPORTE', "Reporté"),
]


class ActionIP(models.Model):
    ip = models.ForeignKey(InformationPreoccupante, on_delete=models.CASCADE, related_name='actions')
    type_action = models.CharField("Type", max_length=20, choices=TYPES_ACTION)
    date = models.DateTimeField("Date et heure")
    duree_minutes = models.PositiveIntegerField("Durée (min)", default=60)
    resultat = models.CharField("Résultat", max_length=15, choices=RESULTATS, default='REALISE')
    enfant = models.ForeignKey('protection_enfance.EnfantIP', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='auditions', verbose_name="Enfant (audition)")
    personnes = models.CharField("Personnes présentes / contactées", max_length=255, blank=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='actions_ip',
                                          verbose_name="Professionnels")
    compte_rendu = models.TextField("Compte rendu", blank=True)
    # Courriers
    date_rdv_propose = models.DateTimeField("Rendez-vous proposé dans le courrier", null=True, blank=True)
    numero_lrar = models.CharField("N° de la LRAR", max_length=40, blank=True)
    date_accuse_reception = models.DateField("Date de l'accusé de réception", null=True, blank=True)
    # Lien avec l'agenda
    creneau = models.ForeignKey('planning.CreneauRdv', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='actions_ip')
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                               related_name='actions_ip_saisies')
    date_saisie = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('date', 'id')
        verbose_name = "Action d'évaluation"

    def __str__(self):
        return f"{self.get_type_action_display()} – {timezone.localtime(self.date):%d/%m/%Y %H:%M}"

    @property
    def est_courrier(self):
        return self.type_action in TYPES_COURRIER


STATUTS_SAISINE = [
    ('PROPOSEE', "Proposée au cadre"),
    ('REFUSEE_CADRE', "Non retenue par le cadre"),
    ('TRANSMISE_PIEF', "Demandée à l'inspecteur"),
    ('REFUSEE_PIEF', "Non validée par l'inspecteur"),
    ('VALIDEE_PIEF', "Validée par l'inspecteur"),
    ('EFFECTUEE', "Procureur saisi"),
]


class SaisineIP(models.Model):
    """Saisine du procureur, possible à tout moment de l'évaluation (danger, famille fuyante…)."""
    ip = models.ForeignKey(InformationPreoccupante, on_delete=models.CASCADE, related_name='saisines')
    motif = models.TextField("Motif (faits, danger constaté)")
    danger_imminent = models.BooleanField("Danger grave et imminent", default=False)
    statut = models.CharField(max_length=20, choices=STATUTS_SAISINE, default='PROPOSEE')
    propose_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    related_name='saisines_proposees')
    date_proposition = models.DateTimeField(auto_now_add=True)
    cadre = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='saisines_cadre')
    date_decision_cadre = models.DateTimeField(null=True, blank=True)
    commentaire_cadre = models.TextField(blank=True)
    inspecteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='saisines_inspecteur')
    date_decision_pief = models.DateTimeField(null=True, blank=True)
    commentaire_pief = models.TextField(blank=True)
    date_saisine = models.DateTimeField("Date de la saisine du procureur", null=True, blank=True)
    reference_parquet = models.CharField("Référence / mode d'envoi", max_length=100, blank=True)
    saisie_directe = models.BooleanField(
        "Saisine directe par le cadre (urgence, inspecteur informé)", default=False)

    class Meta:
        ordering = ('-date_proposition',)
        verbose_name = "Saisine du procureur"

    def __str__(self):
        return f"Saisine {self.ip.numero} – {self.get_statut_display()}"


PRECONISATIONS = [
    ('AUCUNE_SUITE', "Pas de mesure de protection (classement)"),
    ('DROIT_COMMUN', "Accompagnement de droit commun (social, PMI…)"),
    ('AED', "Aide éducative à domicile (AED)"),
    ('SAISINE_JUDICIAIRE', "Saisine de l'autorité judiciaire (AEMO, placement…)"),
    ('AUTRE', "Autre"),
]
AVIS_PIEF = [
    ('ACCORD', "D'accord avec les préconisations"),
    ('AUTRE_SUITE', "Autre suite décidée"),
    ('COMPLEMENT', "Complément d'évaluation demandé"),
]
# Rubriques de la trame, dans l'ordre du rapport (reprises de l'ébauche d'enquête sociale)
RUBRIQUES = [
    ('composition_familiale', "Composition familiale et contexte"),
    ('situation_enfants', "Situation de chaque enfant (santé, scolarité, développement)"),
    ('parole_enfants', "Parole des enfants"),
    ('parole_parents', "Parole des parents"),
    ('conditions_vie', "Conditions de vie"),
    ('partenaires', "Éléments recueillis auprès des partenaires"),
    ('analyse', "Analyse de la situation (danger, risque, ressources de la famille)"),
]


class RapportIP(models.Model):
    ip = models.OneToOneField(InformationPreoccupante, on_delete=models.CASCADE, related_name='rapport')
    composition_familiale = models.TextField(blank=True)
    situation_enfants = models.TextField(blank=True)
    parole_enfants = models.TextField(blank=True)
    parole_parents = models.TextField(blank=True)
    conditions_vie = models.TextField(blank=True)
    partenaires = models.TextField(blank=True)
    analyse = models.TextField(blank=True)
    non_cooperation = models.BooleanField(
        "Famille non coopérante malgré la LRAR (rapport établi avec les éléments recueillis)", default=False)
    preconisation = models.CharField("Préconisation", max_length=20, choices=PRECONISATIONS, blank=True)
    preconisation_detail = models.TextField("Préconisations détaillées", blank=True)

    redige_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='rapports_ip')
    date_modification = models.DateTimeField(auto_now=True)
    date_soumission = models.DateTimeField(null=True, blank=True)
    date_synthese = models.DateField("Date de la réunion de synthèse", null=True, blank=True)
    visa_cadre_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='visas_cadre_ip')
    date_visa_cadre = models.DateTimeField(null=True, blank=True)
    visa_as_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='visas_as_ip')
    date_visa_as = models.DateTimeField(null=True, blank=True)
    # Inspecteur
    avis_pief = models.CharField(max_length=15, choices=AVIS_PIEF, blank=True)
    commentaire_pief = models.TextField(blank=True)
    visa_pief_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='visas_pief_ip')
    date_visa_pief = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Rapport d'évaluation"

    def __str__(self):
        return f"Rapport {self.ip.numero}"

    @property
    def verrouille(self):
        """Une fois soumis en synthèse, le rapport n'est plus modifiable (sauf renvoi)."""
        return self.date_soumission is not None

    @property
    def rubriques(self):
        return [(code, titre, getattr(self, code)) for code, titre in RUBRIQUES]

    @property
    def complet(self):
        return bool(self.analyse.strip() and self.preconisation)
