# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/models/m_expulsion.py
"""Prévention des expulsions locatives : dossier ouvert par le Service Logement (fiche de liaison CD13 – CAF,
assignation aux fins de résiliation de bail) puis suivi avec la MDS, jusqu'au concours de la force publique."""
from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

# Décision du tribunal (cases de la fiche de liaison)
DECISION_CASES = [
    ('present', "Présent ou représenté à l'audience"),
    ('provisions', "Provisions"),
    ('suspension_clause', "Suspension de la clause résolutoire"),
    ('accord_delai', "Accord de délai"),
    ('resiliation', "Résiliation du bail"),
    ('expulsion', "Expulsion"),
    ('delais_paiement', "Délais de paiement"),
    ('delais_quitter', "Délais pour quitter les lieux"),
    ('rejet', "Rejet de la demande de résiliation"),
]
DUREES_DELAI = [('12', "12 mois"), ('24', "24 mois"), ('AUTRE', "Autre")]

# Fiche CAF « Prévention de l'expulsion domiciliaire » : rubriques gardées telles quelles (clé, libellé, rubrique)
CHAMPS_CAF = [
    ('date_edition', "Date d'édition", "Identification de la famille"),
    ('responsable', "Responsable dossier", "Identification de la famille"),
    ('responsable_naissance', "Date de naissance du responsable", "Identification de la famille"),
    ('conjoint', "Conjoint", "Identification de la famille"),
    ('conjoint_naissance', "Date de naissance du conjoint", "Identification de la famille"),
    ('couple_isolement', "Couple ou isolement", "Situation familiale"),
    ('autres_personnes', "Nombre autres personnes", "Situation familiale"),
    ('enfants_pf', "Nombre d'enfants ouvrant droit aux P.F.", "Situation familiale"),
    ('enfants_total', "Nombre d'enfants total", "Situation familiale"),
    ('tutelle', "Tutelle", "Situation familiale"),
    ('regime_resp', "Situation professionnelle (responsable)", "Situation professionnelle, régime"),
    ('regime_conj', "Situation professionnelle (conjoint)", "Situation professionnelle, régime"),
    ('rni', "RNI du foyer", "Ressources familiales"),
    ('qf', "Montant QF CNAF", "Ressources familiales"),
    ('afr', "AFR", "Prestations familiales"), ('apl', "APL", "Prestations familiales"),
    ('asf', "ASF", "Prestations familiales"), ('cfa', "CFA", "Prestations familiales"),
    ('ppi', "PPI", "Prestations familiales"), ('rsi', "RSI", "Prestations familiales"),
    ('mode_versement', "Mode de versement (allocataire, bailleur)", "Logement"),
    ('surface', "Surface (m²)", "Logement"),
    ('montant_loyer', "Montant du loyer", "Logement"),
    ('impaye', "Impayé de loyer", "Logement"),
    ('saisine', "Saisine", "Logement"),
    ('fsl_etat', "FSL (en cours, archivé)", "FSL"),
    ('fsl_commission', "Date de la commission FSL", "FSL"),
    ('fsl_type', "FSL (accès, maintien, garantie)", "FSL"),
    ('fsl_montants', "Montants FSL (subvention, prêt, exonération, solde de prêt)", "FSL"),
    ('fsl_referent', "Référent social FSL", "FSL"),
    ('referent_social', "Référent social", "FSL"),
    ('commentaire', "Commentaire", "Commentaire"),
]


class DossierExpulsion(models.Model):
    """Un ménage menacé d'expulsion. Le Service Logement l'ouvre et l'affecte à une MDS ; la MDS le suit."""
    SL_CAF, PREFECTURE, BAILLEUR, MDS_ORIGINE, AUTRE = 'SL_CAF', 'PREFECTURE', 'BAILLEUR', 'MDS', 'AUTRE'
    ORIGINES = [(SL_CAF, "Assignation – fiche de liaison CD13 / CAF"), (PREFECTURE, "Préfecture (CCAPEX, CFP)"),
                (BAILLEUR, "Bailleur"), (MDS_ORIGINE, "Repéré par la MDS"), (AUTRE, "Autre")]
    OBSERVATIONS_CAF = [('FICHE_CAF', "Fiche CAF"), ('SERVICE_SOCIAL_CAF', "Service social CAF"),
                        ('NON_IDENTIFIE', "Non identifié CAF")]
    BAILLEURS = [('SOCIAL', "Bailleur social"), ('PRIVE', "Bailleur privé (particulier)"),
                 ('PRIVE_MORALE', "Bailleur privé (personne morale)")]
    EN_COURS, CLOS = 'EN_COURS', 'CLOS'
    STATUTS = [(EN_COURS, "En cours"), (CLOS, "Clos")]
    MOTIFS_CLOTURE = [('APUREMENT', "Dette apurée ou plan respecté"), ('DESISTEMENT', "Désistement du bailleur"),
                      ('RELOGEMENT', "Relogement"), ('DEPART', "Départ volontaire"),
                      ('EXPULSION', "Expulsion réalisée"), ('SANS_SUITE', "Sans suite, ménage inconnu"),
                      ('AUTRE', "Autre")]

    numero = models.CharField("N° de dossier", max_length=30, unique=True, blank=True)
    origine = models.CharField(max_length=12, choices=ORIGINES, default=SL_CAF)
    date_reception = models.DateField("Reçu le", default=timezone.localdate)
    mds = models.ForeignKey('mds.MDS', null=True, blank=True, on_delete=models.SET_NULL,
                            related_name='dossiers_expulsion', verbose_name="MDS chargée du suivi")
    referent = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='dossiers_expulsion_suivis', verbose_name="Référent social (MDS)")
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='dossiers_expulsion', verbose_name="Usager rattaché")
    # Locataire (fiche de liaison)
    nom = models.CharField(max_length=100)
    prenom = models.CharField("Prénom", max_length=100, blank=True)
    colocataire = models.CharField("Colocataire", max_length=200, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    code_postal = models.CharField(max_length=10, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    # Propriétaire et bail
    proprietaire = models.TextField("Propriétaire (nom, adresse)", blank=True)
    proprietaire_email = models.EmailField("Mail du bailleur", blank=True,
                                           help_text="Pour lui envoyer le questionnaire par mail plutôt que par courrier.")
    type_bailleur = models.CharField(max_length=15, choices=BAILLEURS, blank=True)
    date_signature_bail = models.DateField("Date de signature du bail", null=True, blank=True)
    loyer_total = models.DecimalField("Montant mensuel total du loyer", max_digits=9, decimal_places=2, null=True, blank=True)
    loyer = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    charges = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    dette = models.DecimalField("Dette réclamée par le bailleur", max_digits=10, decimal_places=2, null=True, blank=True)
    dette_au = models.DateField("Dette arrêtée au", null=True, blank=True)
    # Observations CAF
    numero_allocataire = models.CharField("N° allocataire", max_length=20, blank=True)
    numero_exploc = models.CharField("N° de dossier EXPLOC", max_length=30, blank=True,
                                     help_text="Numéro de la procédure dans l'application de la préfecture.")
    observation_caf = models.CharField(max_length=20, choices=OBSERVATIONS_CAF, blank=True)
    retour_le = models.DateField("Retour le", null=True, blank=True)
    association = models.BooleanField(default=False)
    ccas = models.BooleanField("CCAS", default=False)
    caf = models.JSONField("Fiche CAF", default=dict, blank=True)
    # Audience et décision
    tribunal = models.CharField(max_length=150, blank=True, help_text="Ex. « Tribunal judiciaire de Martigues »")
    date_audience = models.DateField("Date de l'audience", null=True, blank=True)
    heure_audience = models.CharField("Heure", max_length=10, blank=True)
    date_decision = models.DateField("Décision du", null=True, blank=True)
    decision = models.JSONField(default=dict, blank=True)
    # Suivi
    statut = models.CharField(max_length=10, choices=STATUTS, default=EN_COURS)
    motif_cloture = models.CharField(max_length=15, choices=MOTIFS_CLOTURE, blank=True)
    date_cloture = models.DateField(null=True, blank=True)
    anonymise_le = models.DateField("Anonymisé le", null=True, blank=True, editable=False,
                                    help_text="Durée de conservation atteinte : identité effacée, chiffres gardés.")
    observations = models.TextField("Observations du Service Logement", blank=True)
    questionnaire_bailleur_le = models.DateField("Questionnaire envoyé au bailleur le", null=True, blank=True)
    questionnaire_retour_avant = models.DateField("Retour du questionnaire souhaité avant le", null=True, blank=True)
    questionnaire_bailleur_retour = models.DateField("Questionnaire du bailleur reçu le", null=True, blank=True)
    observations_locataire = models.BooleanField("Le locataire a transmis des observations", default=False,
                                                 help_text="Pour le DSF : sans observation, le bordereau de carence peut suivre.")
    historique = models.JSONField(default=list, blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='+')
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dossier de prévention des expulsions"
        verbose_name_plural = "Dossiers de prévention des expulsions"
        ordering = ['-date_reception', '-pk']

    def __str__(self):
        return f"{self.numero} – {self.nom.upper()} {self.prenom}"

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = (self.date_reception or timezone.localdate()).year
            prefixe = f"EXP-{annee}-"
            dernier = (DossierExpulsion.objects.filter(numero__startswith=prefixe)
                       .order_by('-numero').values_list('numero', flat=True).first())
            n = int(dernier.rsplit('-', 1)[1]) + 1 if dernier and dernier.rsplit('-', 1)[1].isdigit() else 1
            self.numero = f"{prefixe}{n:04d}"
        super().save(*args, **kwargs)

    def tracer(self, user, action, detail=""):
        nom = (user.get_full_name() or user.username) if user else "CID"
        self.historique = list(self.historique or []) + [
            {'date': timezone.localtime().strftime('%d/%m/%Y %H:%M'), 'qui': nom, 'action': action, 'detail': detail}]

    @property
    def nom_complet(self):
        return f"{self.nom.upper()} {self.prenom}".strip()

    @property
    def adresse_complete(self):
        return ", ".join(x for x in (self.adresse, f"{self.code_postal} {self.ville}".strip()) if x)

    def libelles_decision(self):
        d = self.decision or {}
        sortie = [lib for cle, lib in DECISION_CASES if d.get(cle)]
        if d.get('provisions') and d.get('provisions_montant'):
            sortie[sortie.index("Provisions")] = f"Provisions : {d['provisions_montant']} €"
        if d.get('accord_delai') and d.get('duree_delai'):
            sortie[sortie.index("Accord de délai")] = f"Accord de délai : {dict(DUREES_DELAI).get(d['duree_delai'], '')}" \
                + (f" ({d['duree_autre']})" if d.get('duree_autre') else "")
        return sortie

    def caf_par_rubrique(self):
        rubriques = {}
        for cle, lib, rub in CHAMPS_CAF:
            if (self.caf or {}).get(cle):
                rubriques.setdefault(rub, []).append((lib, self.caf[cle]))
        return rubriques

    @property
    def etape_courante(self):
        return self.etapes.order_by('-date', '-pk').first()

    @property
    def audience_a_venir(self):
        return bool(self.date_audience and self.date_audience >= timezone.localdate())

    def alertes(self):
        """Ce qui demande une action, du plus urgent au moins urgent (affiché sur le dossier et dans les listes)."""
        if self.statut != self.EN_COURS:
            return []
        j, a = timezone.localdate(), []
        if not self.mds_id:
            a.append("À affecter à une MDS.")
        elif not self.referent_id:
            a.append("Référent social à désigner par la MDS.")
        if self.date_audience:
            jours = (self.date_audience - j).days
            if 0 <= jours <= 30:
                a.append(f"Audience dans {jours} jour(s), le {self.date_audience:%d/%m/%Y}.")
            elif jours < 0 and not self.date_decision:
                a.append("Audience passée : saisir la décision du tribunal.")
        for e in self.etapes.filter(echeance__isnull=False, echeance__lte=j + timedelta(days=15), faite=False):
            a.append(f"{e.get_type_etape_display()} : échéance le {e.echeance:%d/%m/%Y}.")
        audience_a_venir = bool(self.date_audience and self.date_audience >= j)
        for libelle, echeance, fait in self.echeances_dsf():
            if fait or echeance > j + timedelta(days=15) or (echeance < j and not audience_a_venir):
                continue
            a.append(f"{libelle} : " + (f"échéance dépassée ({echeance:%d/%m/%Y})." if echeance < j
                                        else f"avant le {echeance:%d/%m/%Y}."))
        return a

    def echeances_dsf(self):
        """Délais du DSF, en jours ouvrés (note MDS du 27/03/2023, notice CERFA 16227*01) : (libellé, date, fait)."""
        from ..services.jours_ouvres import ajouter, retrancher
        out = []
        signalement = self.etapes.filter(type_etape='SIGNALEMENT').order_by('-date').values_list('date', flat=True).first()
        dsf = self.convocations.filter(type_convocation__in=ConvocationExpulsion.TYPES_DSF)
        if signalement:
            out.append(("Proposer l'entretien DSF au locataire (15 jours ouvrés après le signalement)",
                        ajouter(signalement, 15), dsf.exists()))
        if self.date_audience:
            a = self.date_audience
            out.append(("Nouvel entretien DSF si le locataire ne répond pas (15 jours ouvrés avant l'audience)",
                        retrancher(a, 15), dsf.filter(statut=ConvocationExpulsion.VENU).exists()))
            out.append(("Contacter la CCAPEX locale si elle suit le ménage (10 jours ouvrés avant l'audience)",
                        retrancher(a, 10), False))
            out.append(("Transmettre le DSF ou le bordereau au juge et à la CCAPEX (5 jours ouvrés avant l'audience)",
                        retrancher(a, 5), self.diagnostics.filter(statut=DiagnosticExpulsion.ENVOYE).exists()))
        return out


def treve_hivernale(jour=None):
    """Trêve hivernale : du 1er novembre au 31 mars (aucune expulsion, sauf exceptions prévues par la loi)."""
    jour = jour or timezone.localdate()
    return jour >= date(jour.year, 11, 1) or jour <= date(jour.year, 3, 31)


class EtapeExpulsion(models.Model):
    """Journal de la procédure. Les délais proposés se modifient sur chaque étape."""
    TYPES = [
        ('SIGNALEMENT', "Signalement (CCAPEX, CAF, bailleur)", None),
        ('COMMANDEMENT_PAYER', "Commandement de payer", 42),        # délai pour régler : 6 semaines
        ('ASSIGNATION', "Assignation", None),
        ('QUESTIONNAIRE_BAILLEUR', "Questionnaire envoyé au bailleur", None),
        ('DSF', "Diagnostic social et financier transmis", None),
        ('CARENCE', "Bordereau de carence transmis", None),
        ('AUDIENCE', "Audience", None),
        ('JUGEMENT', "Jugement", None),
        ('SIGNIFICATION', "Signification du jugement", None),
        ('PLAN_APUREMENT', "Plan d'apurement, protocole", None),
        ('COMMANDEMENT_QUITTER', "Commandement de quitter les lieux", 60),   # 2 mois
        ('DEMANDE_CFP', "Demande de concours de la force publique", None),
        ('CAPEX_LOCALE', "CAPEX locale", None),
        ('COMMISSION_PREFECTORALE', "Commission préfectorale", None),
        ('CFP_ACCORDE', "Concours de la force publique accordé", None),
        ('EXPULSION', "Expulsion réalisée", None),
        ('RELOGEMENT', "Relogement, solution trouvée", None),
        ('AUTRE', "Autre", None),
    ]
    CHOIX = [(c, l) for c, l, _ in TYPES]
    DELAIS = {c: d for c, _, d in TYPES if d}

    dossier = models.ForeignKey(DossierExpulsion, on_delete=models.CASCADE, related_name='etapes')
    type_etape = models.CharField("Étape", max_length=25, choices=CHOIX)
    date = models.DateField()
    echeance = models.DateField("Échéance", null=True, blank=True)
    faite = models.BooleanField("Échéance traitée", default=False)
    commentaire = models.TextField(blank=True)
    saisi_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='+')
    saisi_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Étape de la procédure d'expulsion"
        verbose_name_plural = "Étapes de la procédure d'expulsion"
        ordering = ['date', 'pk']

    def __str__(self):
        return f"{self.get_type_etape_display()} – {self.date:%d/%m/%Y}"

    @classmethod
    def echeance_proposee(cls, type_etape, jour):
        d = cls.DELAIS.get(type_etape)
        return jour + timedelta(days=d) if d and jour else None


# ---------------------------------------------------------------------------------------------------------- MDS
class ConvocationExpulsion(models.Model):
    """Rendez-vous proposé au ménage pour le diagnostic social et financier (DSF). Deux sans réponse → carence."""
    DSF_1, DSF_2, COM_1, COM_2 = 'DSF_1', 'DSF_2', 'COM_1', 'COM_2'
    TYPES = [(DSF_1, "1re convocation (DSF)"), (DSF_2, "2e et dernière convocation (DSF)"),
             (COM_1, "Convocation avant commission"), (COM_2, "Relance avant commission")]
    TYPES_DSF = (DSF_1, DSF_2)
    PREVUE, VENU, ABSENT, ANNULE = 'PREVUE', 'VENU', 'ABSENT', 'ANNULE'
    STATUTS = [(PREVUE, "Prévue"), (VENU, "Venu"), (ABSENT, "Absent"), (ANNULE, "Annulée ou reportée")]

    dossier = models.ForeignKey(DossierExpulsion, on_delete=models.CASCADE, related_name='convocations')
    type_convocation = models.CharField(max_length=6, choices=TYPES, default=DSF_1)
    date_courrier = models.DateField("Courrier du", default=timezone.localdate)
    date_rdv = models.DateTimeField("Rendez-vous le")
    lieu = models.CharField(max_length=255, blank=True, help_text="Vide : la MDS")
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='+', verbose_name="Reçu par")
    rdv = models.ForeignKey('planning.CreneauRdv', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    passage = models.ForeignKey('logement.PassageCommission', null=True, blank=True, on_delete=models.CASCADE,
                                related_name='convocations', help_text="Convocation avant une commission")
    statut = models.CharField(max_length=7, choices=STATUTS, default=PREVUE)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='+')
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Convocation (prévention des expulsions)"
        verbose_name_plural = "Convocations (prévention des expulsions)"
        ordering = ['date_rdv']

    def __str__(self):
        return f"{self.get_type_convocation_display()} – {timezone.localtime(self.date_rdv):%d/%m/%Y %H:%M}"


class DiagnosticExpulsion(models.Model):
    """Diagnostic social et financier (Cerfa 16227*01) ou, si le ménage ne s'est jamais présenté, bordereau de
    carence. Visa du cadre en un clic, puis envoi par mail au tribunal et à la préfecture."""
    DSF, CARENCE = 'DSF', 'CARENCE'
    TYPES = [(DSF, "Diagnostic social et financier"), (CARENCE, "Bordereau de carence")]
    BROUILLON, A_VISER, VISE, ENVOYE = 'BROUILLON', 'A_VISER', 'VISE', 'ENVOYE'
    STATUTS = [(BROUILLON, "En rédaction"), (A_VISER, "Visa du cadre demandé"),
               (VISE, "Visé par le cadre : prêt à envoyer"), (ENVOYE, "Transmis")]

    dossier = models.ForeignKey(DossierExpulsion, on_delete=models.CASCADE, related_name='diagnostics')
    type_document = models.CharField(max_length=8, choices=TYPES, default=DSF)
    donnees = models.JSONField(default=dict, blank=True)
    statut = models.CharField(max_length=10, choices=STATUTS, default=BROUILLON)
    redacteur = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='+')
    cadre = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='+', verbose_name="Visé par")
    date_validation_cadre = models.DateTimeField("Visé le", null=True, blank=True)
    date_envoi = models.DateField(null=True, blank=True)
    historique = models.JSONField(default=list, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)
    tracer = DossierExpulsion.tracer

    class Meta:
        verbose_name = "Diagnostic social et financier (ou carence)"
        verbose_name_plural = "Diagnostics sociaux et financiers (ou carences)"
        ordering = ['-cree_le']

    def __str__(self):
        return f"{self.get_type_document_display()} – {self.dossier.numero}"

    @property
    def beneficiaire(self):
        return self.dossier.beneficiaire

    @property
    def mds(self):
        return self.dossier.mds


class DestinataireExpulsion(models.Model):
    """Adresses de transmission, réglées en administration : greffe du tribunal, préfecture (boîte de la
    responsable), CCAPEX… Proposées à l'envoi du DSF ou du bordereau de carence."""
    TRIBUNAL, PREFECTURE, AUTRE = 'TRIBUNAL', 'PREFECTURE', 'AUTRE'
    TYPES = [(TRIBUNAL, "Greffe du tribunal"), (PREFECTURE, "Préfecture, sous-préfecture"), (AUTRE, "Autre")]
    nom = models.CharField(max_length=150, help_text="Ex. « Tribunal judiciaire de … – greffe des contentieux de la protection »")
    type_destinataire = models.CharField(max_length=10, choices=TYPES, default=TRIBUNAL)
    email = models.EmailField()
    mds = models.ManyToManyField('mds.MDS', blank=True, related_name='destinataires_expulsion',
                                 help_text="MDS qui transmettent à cette adresse ; vide : toutes.")
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Destinataire des diagnostics (expulsions)"
        verbose_name_plural = "Destinataires des diagnostics (expulsions)"
        ordering = ['type_destinataire', 'nom']

    def __str__(self):
        return f"{self.nom} <{self.email}>"

    @classmethod
    def pour(cls, mds):
        qs = cls.objects.filter(actif=True)
        return [d for d in qs.prefetch_related('mds') if not d.mds.all() or mds in d.mds.all()]


# ---------------------------------------------------------------------------------------------------- commissions
class CommissionExpulsion(models.Model):
    """Séance d'une instance qui examine les dossiers : CAPEX locale (Martigues / Port-de-Bouc), commission
    préfectorale (environ tous les 6 mois après le jugement, avant le concours de la force publique), CCAPEX."""
    LOCALE, PREFECTORALE, CCAPEX = 'LOCALE', 'PREFECTORALE', 'CCAPEX'
    TYPES = [(LOCALE, "CAPEX locale"), (PREFECTORALE, "Commission préfectorale"), (CCAPEX, "CCAPEX")]
    type_commission = models.CharField("Instance", max_length=12, choices=TYPES, default=LOCALE)
    nom = models.CharField(max_length=150, help_text="Ex. « CAPEX locale Martigues – Port-de-Bouc »")
    date = models.DateField()
    heure = models.CharField(max_length=10, blank=True)
    lieu = models.CharField(max_length=255, blank=True)
    date_limite = models.DateField("Actualisations attendues le", null=True, blank=True)
    email = models.EmailField("Mail du secrétariat", blank=True,
                              help_text="Proposé à l'envoi des actualisations.")
    mds = models.ManyToManyField('mds.MDS', blank=True, related_name='commissions_expulsion',
                                 help_text="MDS concernées ; vide : toutes.")
    tenue = models.BooleanField("Séance tenue", default=False)
    compte_rendu = models.TextField("Observations générales", blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='+')
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Commission (prévention des expulsions)"
        verbose_name_plural = "Commissions (prévention des expulsions)"
        ordering = ['-date']

    def __str__(self):
        return f"{self.nom} – {self.date:%d/%m/%Y}"


class PassageCommission(models.Model):
    """Un dossier inscrit à l'ordre du jour d'une séance : actualisation de la situation par la MDS (visée par le
    cadre), puis avis ou préconisation de la commission."""
    A_FAIRE, A_VISER, VISEE, TRANSMISE = 'A_FAIRE', 'A_VISER', 'VISEE', 'TRANSMISE'
    STATUTS = [(A_FAIRE, "Actualisation à faire"), (A_VISER, "Visa du cadre demandé"),
               (VISEE, "Visée : prête à transmettre"), (TRANSMISE, "Transmise")]
    AVIS = [('MAINTIEN', "Maintien dans les lieux, plan à respecter"), ('DELAI', "Délai supplémentaire"),
            ('ORIENTATION', "Orientation (relogement, hébergement, accompagnement)"),
            ('CFP_FAVORABLE', "Avis favorable au concours de la force publique"),
            ('CFP_DEFAVORABLE', "Avis défavorable au concours de la force publique"),
            ('AJOURNE', "Ajourné, à revoir"), ('AUTRE', "Autre")]

    commission = models.ForeignKey(CommissionExpulsion, on_delete=models.CASCADE, related_name='passages')
    dossier = models.ForeignKey(DossierExpulsion, on_delete=models.CASCADE, related_name='passages')
    actualisation = models.JSONField(default=dict, blank=True)
    statut = models.CharField(max_length=10, choices=STATUTS, default=A_FAIRE)
    redacteur = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='+')
    cadre = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='+', verbose_name="Visé par")
    date_validation_cadre = models.DateTimeField("Visé le", null=True, blank=True)
    date_envoi = models.DateField(null=True, blank=True)
    avis = models.CharField("Avis de la commission", max_length=20, choices=AVIS, blank=True)
    avis_detail = models.TextField("Préconisations", blank=True)
    historique = models.JSONField(default=list, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    tracer = DossierExpulsion.tracer

    class Meta:
        verbose_name = "Dossier inscrit à une commission"
        verbose_name_plural = "Dossiers inscrits aux commissions"
        ordering = ['commission__date', 'dossier__nom']
        unique_together = ('commission', 'dossier')

    def __str__(self):
        return f"{self.dossier} – {self.commission}"

    @property
    def beneficiaire(self):
        return self.dossier.beneficiaire

    @property
    def mds(self):
        return self.dossier.mds
