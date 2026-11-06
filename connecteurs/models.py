# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/models.py
"""
Situation d'un usager auprès des organismes (CAF/MSA, France Travail), rapatriée
par l'API Particulier. Une ligne par usager et par source, mise à jour à chaque
actualisation ; chaque appel est en plus tracé dans le journal (qui, quand, quoi).

Minimisation des données : on ne garde que l'utile pour l'accompagnement
(droit ouvert, date, montant du QF, catégorie d'inscription), jamais les
adresses ni les coordonnées renvoyées par les organismes.
"""
from django.conf import settings
from django.db import models


SOURCES = [
    ('RSA', "RSA"),
    ('PRIME_ACTIVITE', "Prime d'activité"),
    ('QUOTIENT_FAMILIAL', "Quotient familial CAF / MSA"),
    ('ASF', "Allocation de soutien familial"),
    ('AAH', "Allocation adulte handicapé"),
    ('C2S', "Complémentaire santé solidaire"),
    ('FRANCE_TRAVAIL', "Inscription France Travail"),
]

STATUTS_APPEL = [
    ('OK', "Information reçue"),
    ('NON_TROUVE', "Personne non trouvée"),
    ('INCOMPLET', "Fiche incomplète"),
    ('ERREUR', "Service indisponible"),
]


class SituationExterne(models.Model):
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE,
                                     related_name='situations_externes')
    source = models.CharField(max_length=20, choices=SOURCES)
    statut_appel = models.CharField(max_length=12, choices=STATUTS_APPEL)
    resume = models.CharField(max_length=255, help_text="Phrase affichée à l'agent")
    est_beneficiaire = models.BooleanField(null=True, blank=True)
    donnees = models.JSONField(default=dict, blank=True, help_text="Données utiles uniquement (minimisées)")
    date_maj = models.DateTimeField(help_text="Date de dernière mise à jour de l'information")
    maj_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='+')
    environnement = models.CharField(max_length=15, default='bac_a_sable')

    class Meta:
        unique_together = ('beneficiaire', 'source')
        ordering = ['source']
        verbose_name = "Situation externe (API Particulier)"
        verbose_name_plural = "Situations externes (API Particulier)"

    def __str__(self):
        return f"{self.beneficiaire} – {self.get_source_display()} : {self.resume}"


class JournalAppelAPI(models.Model):
    """Traçabilité : chaque consultation d'un organisme par un agent."""
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE,
                                     related_name='+')
    source = models.CharField(max_length=20, choices=SOURCES)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    related_name='+')
    date = models.DateTimeField(auto_now_add=True)
    code_http = models.PositiveSmallIntegerField(null=True, blank=True)
    statut_appel = models.CharField(max_length=12, choices=STATUTS_APPEL)
    environnement = models.CharField(max_length=15, default='bac_a_sable')

    class Meta:
        ordering = ['-date']
        verbose_name = "Journal des appels API Particulier"
        verbose_name_plural = "Journal des appels API Particulier"


# -----------------------------------------------------------------------------
# Passerelle RDV Service Public (ANCT) — désactivée tant que RDVSP_ACTIF n'est pas à 1
# -----------------------------------------------------------------------------
class CompteRDVSP(models.Model):
    """Connexion d'un agent CID à son compte RDV Service Public (OAuth2, un jeton par agent)."""
    utilisateur = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                       related_name='compte_rdvsp')
    agent_id = models.CharField(max_length=30, blank=True, help_text="Identifiant de l'agent côté RDV Service Public")
    jeton_acces = models.TextField()
    jeton_renouvellement = models.TextField(blank=True)
    expire_le = models.DateTimeField()
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Compte RDV Service Public d'un agent"
        verbose_name_plural = "Comptes RDV Service Public des agents"

    def __str__(self):
        return f"{self.utilisateur} (agent RDV-SP {self.agent_id or '?'})"


class LienUsagerRDVSP(models.Model):
    """Correspondance entre un usager CID et son identifiant usager côté RDV Service Public."""
    beneficiaire = models.OneToOneField('beneficiaire.Beneficiaire', on_delete=models.CASCADE,
                                        related_name='lien_rdvsp')
    usager_rdvsp_id = models.CharField(max_length=30)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lien usager ↔ RDV Service Public"
        verbose_name_plural = "Liens usagers ↔ RDV Service Public"

    def __str__(self):
        return f"{self.beneficiaire} → usager RDV-SP {self.usager_rdvsp_id}"


class AppelRDVSP(models.Model):
    """Traçabilité de chaque appel à RDV Service Public (qui, quand, pour quel usager, résultat)."""
    ACTIONS = [
        ('CONNEXION', "Connexion de l'agent"),
        ('PLAN_RDV', "Préparation d'un rendez-vous"),
        ('LISTE_RDV', "Lecture des rendez-vous"),
        ('STATUT_RDV', "Mise à jour du statut d'un rendez-vous"),
        ('SYNCHRO', "Synchronisation de l'agenda"),
        ('AVIS', "Avis reçu de RDV-Solidarités"),
    ]
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    related_name='+')
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE, null=True,
                                     blank=True, related_name='+')
    action = models.CharField(max_length=12, choices=ACTIONS)
    code_http = models.PositiveSmallIntegerField(null=True, blank=True)
    reussi = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "Journal des appels RDV Service Public"
        verbose_name_plural = "Journal des appels RDV Service Public"


# -----------------------------------------------------------------------------
# Synchronisation des agendas CID → RDV-Solidarités (étape 1) — connecteurs/rdvsp_synchro.py
# CID est l'agenda maître : il publie ses demi-journées de réception, bloque ce qui est pris chez lui,
# et reçoit les RDV pris en ligne. Rien ne se passe tant que la passerelle n'est pas activée.
# -----------------------------------------------------------------------------
def prefixe_references():
    """
    Préfixe des références CID envoyées à RDV-Solidarités (lieux, motifs, permanences). RDV-Solidarités refuse
    une référence déjà utilisée par la même application : chaque serveur CID (démo, production…) qui partage
    les mêmes identifiants OAuth doit avoir son propre préfixe (variable RDVSP_PREFIXE, défaut « cid »).
    """
    import os
    return os.environ.get("RDVSP_PREFIXE", "").strip() or "cid"


class ParametresRDVSP(models.Model):
    """Réglages de la synchronisation (une seule ligne)."""
    compte_synchro = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        help_text="Compte CID qui synchronise (relié une fois à RDV-Solidarités ; administrateur de l'espace "
                  "départemental côté RDV-Solidarités)")
    service_sp_id = models.PositiveIntegerField(null=True, blank=True,
                                                help_text="Identifiant du service « social » côté RDV-Solidarités")
    semaines_publication = models.PositiveSmallIntegerField(default=8, help_text="Durée de chaque publication")
    derniere_synchro = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Réglages RDV-Solidarités"
        verbose_name_plural = "Réglages RDV-Solidarités"

    def __str__(self):
        return "Réglages RDV-Solidarités"

    @classmethod
    def get(cls):
        return cls.objects.get_or_create(pk=1)[0]


class MdsRDVSP(models.Model):
    """Une MDS de CID = une organisation de RDV-Solidarités."""
    mds = models.OneToOneField('mds.MDS', on_delete=models.CASCADE, related_name='rdvsp')
    organisation_sp_id = models.PositiveIntegerField(help_text="Identifiant de l'organisation côté RDV-Solidarités")
    en_ligne = models.BooleanField(default=False, help_text="Publier les permanences de cette MDS en ligne")
    lieu_sp_id = models.PositiveIntegerField(null=True, blank=True, editable=False)
    avis_declare = models.BooleanField(default=False, editable=False,
                                       help_text="Adresse de CID déclarée pour les avis automatiques")

    class Meta:
        verbose_name = "MDS dans RDV-Solidarités"
        verbose_name_plural = "MDS dans RDV-Solidarités"

    def __str__(self):
        return f"{self.mds} → organisation {self.organisation_sp_id}"

    @property
    def reference_lieu(self):
        return f"{prefixe_references()}-mds-{self.mds_id}"


class MotifRDVSP(models.Model):
    """Motif ouvert à la réservation en ligne (étape 1 : « Renouvellement RSA » seulement)."""
    nom = models.CharField(max_length=100, default="Renouvellement RSA")
    duree_minutes = models.PositiveSmallIntegerField(default=30)
    delai_min_heures = models.PositiveSmallIntegerField(default=48, help_text="Réservation en ligne au plus tard N heures avant")
    delai_max_jours = models.PositiveSmallIntegerField(default=15, help_text="Réservation en ligne au plus tôt N jours avant")
    plafond_demi_journee = models.PositiveSmallIntegerField(
        default=2, help_text="RDV pris en ligne au maximum par demi-journée (l'accueil peut en placer d'autres)")
    sur_invitation = models.BooleanField(default=True, help_text="Réservable seulement par les usagers invités")
    couleur = models.CharField(max_length=7, default="#1e3a8a")
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Motif ouvert en ligne"
        verbose_name_plural = "Motifs ouverts en ligne"

    def __str__(self):
        return self.nom

    def reference(self, mds_sp):
        return f"{prefixe_references()}-motif-{self.pk}-mds-{mds_sp.mds_id}"


class MotifRDVSPPublie(models.Model):
    motif = models.ForeignKey(MotifRDVSP, on_delete=models.CASCADE, related_name='publications')
    mds_sp = models.ForeignKey(MdsRDVSP, on_delete=models.CASCADE, related_name='motifs')
    motif_sp_id = models.PositiveIntegerField()

    class Meta:
        unique_together = ('motif', 'mds_sp')


class PlageRDVSP(models.Model):
    """Demi-journée de réception publiée (permanence hebdomadaire, sur une période limitée)."""
    demi_journee = models.ForeignKey('mds.DemiJourneeReception', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='plages_rdvsp')
    mds = models.ForeignKey('mds.MDS', on_delete=models.CASCADE, related_name='+')
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    jour_semaine = models.PositiveSmallIntegerField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    premier_jour = models.DateField()
    dernier_jour = models.DateField()
    plage_sp_id = models.PositiveIntegerField()
    neutralisee = models.BooleanField(default=False, help_text="Retirée dans CID : neutralisée par une absence")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['premier_jour']
        verbose_name = "Permanence publiée"
        verbose_name_plural = "Permanences publiées"

    def __str__(self):
        return f"{self.agent} – {self.premier_jour:%d/%m} → {self.dernier_jour:%d/%m} {self.heure_debut:%H:%M}-{self.heure_fin:%H:%M}"

    def couvre(self, jour, debut=None, fin=None):
        if self.neutralisee or not (self.premier_jour <= jour <= self.dernier_jour) or jour.weekday() != self.jour_semaine:
            return False
        if debut is not None and fin is not None:
            return debut < self.heure_fin and fin > self.heure_debut
        return True


class AbsenceRDVSP(models.Model):
    """Indisponibilité envoyée à RDV-Solidarités : ce qui est pris ou fermé dans CID n'est pas réservable en ligne."""
    CRENEAU, PLAFOND, JOUR_BLOQUE, RETRAIT = 'CRENEAU', 'PLAFOND', 'JOUR_BLOQUE', 'RETRAIT'
    RAISONS = [(CRENEAU, "Créneau pris dans CID"), (PLAFOND, "Plafond de RDV en ligne atteint"),
               (JOUR_BLOQUE, "Jour bloqué dans CID"), (RETRAIT, "Permanence retirée dans CID")]
    raison = models.CharField(max_length=12, choices=RAISONS)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    absence_sp_id = models.PositiveIntegerField()
    creneau = models.ForeignKey('planning.CreneauRdv', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    jour_bloque = models.ForeignKey('planning.JourBloque', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    plage = models.ForeignKey(PlageRDVSP, on_delete=models.SET_NULL, null=True, blank=True, related_name='absences')
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Blocage envoyé"
        verbose_name_plural = "Blocages envoyés"


class RdvRDVSP(models.Model):
    """RDV venu de RDV-Solidarités, rattaché à un créneau de l'agenda CID."""
    rdv_sp_id = models.PositiveIntegerField(unique=True)
    creneau = models.OneToOneField('planning.CreneauRdv', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='rdvsp')
    mds = models.ForeignKey('mds.MDS', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='+')
    usager_sp_id = models.PositiveIntegerField(null=True, blank=True)
    motif = models.CharField(max_length=150, blank=True)
    debut = models.DateTimeField()
    fin = models.DateTimeField()
    cree_par_usager = models.BooleanField(default=False, help_text="Réservé en ligne par l'usager lui-même")
    statut_sp = models.CharField(max_length=20, blank=True)
    annule_le = models.DateTimeField(null=True, blank=True)
    a_rapprocher = models.BooleanField(default=False, help_text="Usager ou agent non retrouvé dans CID")
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-debut']
        verbose_name = "RDV pris dans RDV-Solidarités"
        verbose_name_plural = "RDV pris dans RDV-Solidarités"

    def __str__(self):
        return f"RDV {self.rdv_sp_id} – {self.motif} – {self.debut:%d/%m/%Y %H:%M}"

    @property
    def actif(self):
        return self.statut_sp not in ('excused', 'revoked') and not self.annule_le


class AvisRDVSP(models.Model):
    """Avis automatique reçu de RDV-Solidarités (webhook). Contenu effacé au bout de 30 jours."""
    recu_le = models.DateTimeField(auto_now_add=True)
    modele = models.CharField(max_length=40, blank=True)
    evenement = models.CharField(max_length=20, blank=True)
    objet_sp_id = models.PositiveIntegerField(null=True, blank=True)
    traite = models.BooleanField(default=False)
    erreur = models.CharField(max_length=500, blank=True)
    corps = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-recu_le']
        verbose_name = "Avis reçu de RDV-Solidarités"
        verbose_name_plural = "Avis reçus de RDV-Solidarités"
