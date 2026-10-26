# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/models/m_ip.py
"""
Information préoccupante (IP) : circuit complet CRIP → MDS → inspecteur enfance famille (PIEF).

  1. La CRIP reçoit l'IP (le délai de 3 mois court à partir de cette date) et la transmet à une MDS.
  2. Le cadre de la MDS réunit l'équipe (réunion IP), CID propose un binôme, le cadre le valide.
  3. Le binôme évalue : courriers, LRAR, appels, rendez-vous, auditions, VAD… tout est enregistré.
  4. Rapport et préconisations → réunion de synthèse → visas du cadre et de l'AS.
  5. Envoi à l'inspecteur (PIEF), qui contresigne ou propose une autre suite → clôture.
"""
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import models
from django.utils import timezone

from .m_generique import generate_numero

DELAI_MOIS = 3                    # l'évaluation doit être terminée dans les 3 mois suivant la réception par la CRIP
DELAI_INTERMEDIAIRE_JOURS = 60    # point de rappel : le cadre relance le binôme, réunion de point si besoin
AGE_PMI = 5                       # enfant de 5 ans ou moins : CID propose un professionnel de PMI dans le binôme

# Capacités
CAP_CRIP = 'ip_crip'              # CRIP : réception et transmission aux MDS (voit toutes les IP)
CAP_PIEF = 'ip_pief'              # inspecteur enfance famille : visa du rapport, saisine du procureur
CAP_PILOTER = 'ip_piloter'        # cadre de MDS : réunions, binôme, visas, décisions
CAP_EVALUER = 'ip_evaluer'        # TS / PMI pouvant faire partie d'un binôme

STATUTS = [
    ('RECUE', "Reçue par la CRIP"),
    ('TRANSMISE_MDS', "Transmise à la MDS"),
    ('EN_EVALUATION', "Évaluation en cours"),
    ('SYNTHESE', "Rapport en synthèse"),
    ('TRANSMISE_PIEF', "Transmise à l'inspecteur"),
    ('CLOTUREE', "Clôturée"),
]
STATUTS_OUVERTS = ('RECUE', 'TRANSMISE_MDS', 'EN_EVALUATION', 'SYNTHESE')
BADGES = {
    'RECUE': 'bg-gray-100 text-gray-800', 'TRANSMISE_MDS': 'bg-amber-100 text-amber-800',
    'EN_EVALUATION': 'bg-blue-100 text-blue-800', 'SYNTHESE': 'bg-purple-100 text-purple-800',
    'TRANSMISE_PIEF': 'bg-indigo-100 text-indigo-800', 'CLOTUREE': 'bg-emerald-100 text-emerald-800',
}

ORIGINES = [
    ('NUM_119', 'Numéro « enfance en danger » (119)'),
    ('EDUCATION', 'Éducation nationale'),
    ('SANTE', 'Professionnel de santé'),
    ('MDS', 'Maison départementale de la solidarité'),
    ('PARTENAIRE', 'Autre partenaire (association, service…)'),
    ('PARTICULIER', 'Particulier, famille, voisinage'),
    ('AUTRE_DEPARTEMENT', 'Autre département'),
    ('AUTRE', 'Autre'),
]
URGENCES = [
    ('IMMEDIATE', 'Immédiate (danger grave et imminent)'),
    ('RAPIDE', 'Rapide'),
    ('COURANTE', 'Courante'),
    ('DIFFERE', 'Différée'),
]
DECISIONS_FINALES = [
    ('CLASSEMENT', "Classement : pas de mesure de protection"),
    ('DROIT_COMMUN', "Accompagnement de droit commun (social, PMI…)"),
    ('AED', "Aide éducative à domicile (AED)"),
    ('SAISINE_PROCUREUR', "Saisine du procureur (AEMO, placement…)"),
    ('AUTRE', "Autre suite"),
]


def cadre_ip(mds):
    """Cadre qui pilote les IP d'une MDS : adjoint enfance famille s'il y en a un, sinon le responsable."""
    if not mds:
        return None
    from mds.models import UserMDSProfile
    ump = (UserMDSProfile.objects.filter(mds=mds, actif=True, user__is_active=True,
                                         user__profils__code='MDS_ADJOINT_ENFANCE_FAMILLE')
           .select_related('user').first())
    if ump:
        return ump.user
    from beneficiaire.transfert import responsable_mds
    return responsable_mds(mds)


class InformationPreoccupante(models.Model):
    # ------------------------------------------------------------------ identification
    numero = models.CharField(max_length=20, unique=True, db_index=True, editable=False)
    date_reception_crip = models.DateField("Date de réception par la CRIP",
                                           help_text="Le délai de 3 mois court à partir de cette date.")
    recue_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name='ip_recues', verbose_name="Agent CRIP")
    origine = models.CharField(max_length=32, choices=ORIGINES, default='AUTRE')
    niveau_urgence = models.CharField("Urgence", max_length=12, choices=URGENCES, default='COURANTE')
    description = models.TextField("Faits rapportés")
    situation_particuliere = models.CharField(
        "Situation particulière", max_length=200, blank=True,
        help_text="Grossesse, handicap… : CID proposera un professionnel de PMI dans le binôme.")

    # ------------------------------------------------------------------ déclarant (masqué aux MDS)
    signalant_nom = models.CharField("Nom du déclarant", max_length=150, blank=True)
    signalant_qualite = models.CharField("Qualité", max_length=100, blank=True)
    signalant_structure = models.CharField("Structure", max_length=200, blank=True)
    signalant_contact = models.TextField("Coordonnées", blank=True)
    signalant_confidentialite = models.BooleanField("Le déclarant demande la confidentialité", default=False)

    # ------------------------------------------------------------------ famille
    famille = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='informations_preoccupantes',
                                verbose_name="Dossier de la famille dans CID")
    famille_libelle = models.CharField("Famille (si pas encore de dossier CID)", max_length=200, blank=True)
    famille_adresse = models.TextField("Adresse de la famille", blank=True)

    # ------------------------------------------------------------------ MDS
    mds = models.ForeignKey('mds.MDS', on_delete=models.PROTECT, null=True, blank=True,
                            related_name='informations_preoccupantes', verbose_name="MDS en charge")
    mds_partage = models.ManyToManyField('mds.MDS', related_name='ip_partage', blank=True,
                                         verbose_name="MDS associées (enquête conjointe)")
    autre_departement = models.CharField(
        "Autre département concerné", max_length=200, blank=True,
        help_text="Parents sur deux départements (enquête conjointe), déménagement…")

    # ------------------------------------------------------------------ binôme
    binome_1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='ip_binome_1', verbose_name="Référent 1")
    binome_2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='ip_binome_2', verbose_name="Référent 2")
    binome_valide_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                          blank=True, related_name='ip_binomes_valides')
    date_binome = models.DateTimeField(null=True, blank=True)

    # ------------------------------------------------------------------ circuit et délais
    statut = models.CharField(max_length=20, choices=STATUTS, default='RECUE')
    date_transmission_mds = models.DateTimeField(null=True, blank=True)
    date_intermediaire = models.DateField(null=True, blank=True, editable=False)
    date_echeance = models.DateField(null=True, blank=True, editable=False)
    rappel_intermediaire_envoye = models.BooleanField(default=False)
    rappel_echeance_envoye = models.BooleanField(default=False)
    date_transmission_pief = models.DateTimeField("Envoi à l'inspecteur (fin réelle)", null=True, blank=True)

    # ------------------------------------------------------------------ décision de l'inspecteur
    inspecteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='ip_inspectees')
    decision_finale = models.CharField(max_length=20, choices=DECISIONS_FINALES, blank=True)
    decision_commentaire = models.TextField(blank=True)
    date_cloture = models.DateTimeField(null=True, blank=True)

    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='ip_creees')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-date_reception_crip', '-id')
        verbose_name = "Information préoccupante"
        verbose_name_plural = "Informations préoccupantes"

    def __str__(self):
        return f"{self.numero} – {self.libelle_famille}"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = generate_numero('D13')
        if self.date_reception_crip:
            self.date_echeance = self.date_reception_crip + relativedelta(months=DELAI_MOIS)
            self.date_intermediaire = self.date_reception_crip + timedelta(days=DELAI_INTERMEDIAIRE_JOURS)
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------ affichage
    @property
    def libelle_famille(self):
        if self.famille_id:
            return f"{self.famille.nom.upper()} {self.famille.prenom}"
        return self.famille_libelle or "Famille non renseignée"

    @property
    def badge(self):
        return BADGES.get(self.statut, 'bg-gray-100 text-gray-800')

    @property
    def binome(self):
        return [u for u in (self.binome_1, self.binome_2) if u]

    # ------------------------------------------------------------------ délais
    @property
    def date_fin_reelle(self):
        return timezone.localtime(self.date_transmission_pief).date() if self.date_transmission_pief else None

    @property
    def jours_restants(self):
        if not self.date_echeance or self.date_transmission_pief:
            return None
        return (self.date_echeance - timezone.localdate()).days

    @property
    def delai_respecte(self):
        """True / False une fois le rapport parti chez l'inspecteur ; None tant que l'évaluation court."""
        if not self.date_fin_reelle:
            return None
        return self.date_fin_reelle <= self.date_echeance

    @property
    def depassement_jours(self):
        fin = self.date_fin_reelle or (timezone.localdate() if self.statut in STATUTS_OUVERTS else None)
        if not fin or not self.date_echeance:
            return 0
        return max(0, (fin - self.date_echeance).days)

    @property
    def alerte(self):
        """'retard', 'proche' (point intermédiaire passé) ou None — pour les couleurs des listes."""
        if self.statut not in STATUTS_OUVERTS:
            return None
        aujourdhui = timezone.localdate()
        if self.date_echeance and aujourdhui > self.date_echeance:
            return 'retard'
        if self.date_intermediaire and aujourdhui >= self.date_intermediaire:
            return 'proche'
        return None

    # ------------------------------------------------------------------ droits
    def est_binome(self, user):
        return user.pk is not None and user.pk in (self.binome_1_id, self.binome_2_id)

    def _mds_de_l_ip(self):
        return [m for m in [self.mds] + list(self.mds_partage.all()) if m]

    def peut_piloter(self, user):
        """Cadre (ou adjoint) d'une MDS en charge de l'IP."""
        if user.is_superuser:
            return True
        return user.a_la_capacite(CAP_PILOTER) and any(user.a_acces_mds(m) for m in self._mds_de_l_ip())

    def peut_voir(self, user):
        """Accès restreint : CRIP, inspecteurs, cadres de la MDS en charge, binôme."""
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.a_la_capacite(CAP_CRIP) or user.a_la_capacite(CAP_PIEF):
            return True
        return self.est_binome(user) or self.peut_piloter(user)

    def peut_evaluer(self, user):
        """Enregistrer des actions, rédiger le rapport : binôme et cadres de la MDS."""
        return self.statut == 'EN_EVALUATION' and (self.est_binome(user) or self.peut_piloter(user))

    def peut_modifier_crip(self, user):
        return user.a_la_capacite(CAP_CRIP) and self.statut in ('RECUE', 'TRANSMISE_MDS')

    @staticmethod
    def voit_declarant(user):
        """L'identité du déclarant n'est visible que de la CRIP et des inspecteurs."""
        return user.is_superuser or user.a_la_capacite(CAP_CRIP) or user.a_la_capacite(CAP_PIEF)

    @classmethod
    def visibles_par(cls, user):
        from django.db.models import Q
        qs = cls.objects.all()
        if user.is_superuser or user.a_la_capacite(CAP_CRIP) or user.a_la_capacite(CAP_PIEF):
            return qs
        filtre = Q(binome_1=user) | Q(binome_2=user)
        if user.a_la_capacite(CAP_PILOTER):
            from mds.models import UserMDSProfile
            mds_ids = list(UserMDSProfile.objects.filter(user=user, actif=True).values_list('mds_id', flat=True))
            filtre |= Q(mds_id__in=mds_ids) | Q(mds_partage__in=mds_ids)
        return qs.filter(filtre).distinct()


class EnfantIP(models.Model):
    """Enfant concerné par l'IP (souvent une fratrie). Relié au dossier CID quand il existe."""
    ip = models.ForeignKey(InformationPreoccupante, on_delete=models.CASCADE, related_name='enfants')
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name='ip_concernees')
    nom = models.CharField(max_length=60)
    prenom = models.CharField(max_length=60)
    date_naissance = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ('date_naissance', 'id')
        verbose_name = "Enfant concerné"

    def __str__(self):
        return f"{self.prenom} {self.nom.upper()}"

    @property
    def age(self):
        if not self.date_naissance:
            return None
        return relativedelta(timezone.localdate(), self.date_naissance).years

    @property
    def releve_pmi(self):
        return self.age is not None and self.age <= AGE_PMI
