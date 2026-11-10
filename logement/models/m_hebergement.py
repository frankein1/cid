# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/models/m_hebergement.py
"""Hébergement d'urgence : dossier ouvert par la MDS pour un ménage en rupture d'hébergement, démarches préalables
(115, SIAO, centres maternels, DAHO…), fiches transmises au service départemental qui appuie les MDS (demande,
renouvellement, rapport final, orientation vers les services de l'État), prise en charge et échéances.

Les structures d'hébergement et les adresses de transmission sont réglées en administration : rien de local n'est
écrit dans le code."""
from django.conf import settings
from django.db import models
from django.utils import timezone

from .m_expulsion import DossierExpulsion


class StructureHebergement(models.Model):
    """Structure d'accueil (référentiel local, saisi en administration). Les durées servent à proposer la date de fin
    de prise en charge ; vides : 3 mois, renouvelables 3 mois puis par périodes de 2 mois."""
    nom = models.CharField(max_length=150)
    ville = models.CharField(max_length=100, blank=True)
    public = models.CharField("Public accueilli", max_length=255, blank=True)
    duree_initiale_jours = models.PositiveSmallIntegerField("Durée d'accueil (jours)", null=True, blank=True)
    duree_renouvellement_jours = models.PositiveSmallIntegerField("Durée d'un renouvellement (jours)", null=True,
                                                                  blank=True)
    contact = models.TextField("Contact (interne)", blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Structure d'hébergement d'urgence"
        verbose_name_plural = "Structures d'hébergement d'urgence"
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.ville})" if self.ville else self.nom


class DestinataireHebergement(models.Model):
    """Adresse à laquelle les fiches sont transmises (boîte générique du service départemental), en administration."""
    nom = models.CharField(max_length=150, help_text="Ex. « Service d'appui à l'hébergement »")
    email = models.EmailField()
    est_sas = models.BooleanField("Adresse du SAS (fiches DDETS)", default=False,
                                  help_text="La fiche DDETS ne se transmet que par le SAS.")
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Destinataire des fiches d'hébergement d'urgence"
        verbose_name_plural = "Destinataires des fiches d'hébergement d'urgence"
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} <{self.email}>"


class DossierHebergement(models.Model):
    RECHERCHE, HEBERGE, CLOS = 'RECHERCHE', 'HEBERGE', 'CLOS'
    STATUTS = [(RECHERCHE, "Recherche d'une solution"), (HEBERGE, "Hébergé en structure"), (CLOS, "Clos")]
    MOTIFS_CLOTURE = [('LOGEMENT', "Accès à un logement"), ('HEBERGEMENT', "Hébergement durable (CHRS, résidence…)"),
                      ('MATERNEL', "Centre maternel"), ('PERSONNELLE', "Solution personnelle (famille, amis)"),
                      ('ETAT', "Prise en charge par les services de l'État"),
                      ('SANS_SUITE', "Demande sans suite ou refusée"), ('PERDU_DE_VUE', "Ménage perdu de vue"),
                      ('DEPART', "Départ de la structure sans solution connue"), ('AUTRE', "Autre")]

    numero = models.CharField(max_length=14, unique=True, editable=False)
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', null=True, on_delete=models.CASCADE,
                                     related_name='dossiers_hebergement')
    mds = models.ForeignKey('mds.MDS', on_delete=models.PROTECT, related_name='dossiers_hebergement')
    referent = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='+', verbose_name="Référent social")
    statut = models.CharField(max_length=10, choices=STATUTS, default=RECHERCHE)
    date_ouverture = models.DateField(default=timezone.localdate)
    structure = models.ForeignKey(StructureHebergement, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='dossiers')
    structure_libre = models.CharField("Autre structure", max_length=150, blank=True)
    date_entree = models.DateField("Entrée dans la structure", null=True, blank=True)
    date_fin_prevue = models.DateField("Fin de prise en charge prévue", null=True, blank=True)
    date_sortie = models.DateField("Sortie de la structure", null=True, blank=True)
    motif_cloture = models.CharField(max_length=14, choices=MOTIFS_CLOTURE, blank=True)
    date_cloture = models.DateField(null=True, blank=True)
    alerte_pour = models.DateField(null=True, blank=True, editable=False,
                                   help_text="Échéance pour laquelle le référent a déjà été prévenu")
    anonymise_le = models.DateField(null=True, blank=True, editable=False)
    historique = models.JSONField(default=list, blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='+')
    cree_le = models.DateTimeField(auto_now_add=True)
    tracer = DossierExpulsion.tracer

    class Meta:
        verbose_name = "Dossier d'hébergement d'urgence"
        verbose_name_plural = "Dossiers d'hébergement d'urgence"
        ordering = ['-date_ouverture', '-pk']

    def __str__(self):
        return f"{self.numero} – {self.nom_complet}"

    def save(self, *args, **kwargs):
        if not self.numero:
            annee = (self.date_ouverture or timezone.localdate()).year
            dernier = (DossierHebergement.objects.filter(numero__startswith=f"HU-{annee}-")
                       .order_by('-numero').values_list('numero', flat=True).first())
            self.numero = f"HU-{annee}-{(int(dernier[-4:]) + 1 if dernier else 1):04d}"
        super().save(*args, **kwargs)

    @property
    def nom_complet(self):
        b = self.beneficiaire
        return f"{b.nom.upper()} {b.prenom}" if b else "ANONYME"

    @property
    def nom_structure(self):
        return str(self.structure) if self.structure else self.structure_libre

    @property
    def jours_restants(self):
        if self.statut != self.HEBERGE or not self.date_fin_prevue:
            return None
        return (self.date_fin_prevue - timezone.localdate()).days

    @property
    def nb_renouvellements(self):
        return self.fiches.filter(type_fiche=FicheHebergement.RENOUVELLEMENT, reponse=FicheHebergement.ACCORD).count()


class DemarcheHebergement(models.Model):
    """Démarche préalable ou parallèle : la trace écrite attendue avant toute demande (et utile en cas de recours)."""
    TYPES = [('115', "Appel au 115"), ('SIAO', "Fiche SIAO instruite ou mise à jour"),
             ('CENTRE_MATERNEL', "Centre maternel"), ('MECS', "Accueil mère-enfants (MECS, foyer)"),
             ('DAHO', "Recours DAHO"), ('DALO', "Recours DALO"), ('RESEAU', "Solution personnelle (famille, amis, hôtel)"),
             ('AUTRE', "Autre")]
    dossier = models.ForeignKey(DossierHebergement, on_delete=models.CASCADE, related_name='demarches')
    type_demarche = models.CharField(max_length=16, choices=TYPES)
    date = models.DateField(default=timezone.localdate)
    precision = models.CharField("Précision (lequel ?)", max_length=150, blank=True)
    reponse = models.CharField("Réponse, proposition", max_length=255, blank=True)
    saisi_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='+')

    class Meta:
        verbose_name = "Démarche d'hébergement"
        verbose_name_plural = "Démarches d'hébergement"
        ordering = ['date', 'pk']

    def __str__(self):
        return f"{self.get_type_demarche_display()} – {self.date:%d/%m/%Y}"


class FicheHebergement(models.Model):
    """Fiche transmise au service départemental : toujours avec le visa du cadre (initiales et date)."""
    SAS, RENOUVELLEMENT, FINAL, ETAT = 'SAS', 'RENOUV', 'FINAL', 'ETAT'
    TYPES = [(SAS, "Demande d'hébergement d'urgence"), (RENOUVELLEMENT, "Renouvellement de la prise en charge"),
             (FINAL, "Rapport final de prise en charge"), (ETAT, "Orientation vers les services de l'État (DDETS)")]
    BROUILLON, A_VISER, VISEE, ENVOYEE = 'BROUILLON', 'A_VISER', 'VISEE', 'ENVOYEE'
    STATUTS = [(BROUILLON, "En rédaction"), (A_VISER, "Visa du cadre demandé"),
               (VISEE, "Visée par le cadre : prête à envoyer"), (ENVOYEE, "Transmise")]
    ACCORD, REFUS, AJOURNEMENT = 'ACCORD', 'REFUS', 'AJOURNEMENT'
    REPONSES = [(ACCORD, "Accord"), (AJOURNEMENT, "Ajournement (à compléter)"), (REFUS, "Refus ou pas de place")]

    dossier = models.ForeignKey(DossierHebergement, on_delete=models.CASCADE, related_name='fiches')
    type_fiche = models.CharField(max_length=6, choices=TYPES, default=SAS)
    donnees = models.JSONField(default=dict, blank=True)
    statut = models.CharField(max_length=10, choices=STATUTS, default=BROUILLON)
    redacteur = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='+')
    cadre = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='+', verbose_name="Visé par")
    date_validation_cadre = models.DateTimeField("Visé le", null=True, blank=True)
    date_envoi = models.DateField(null=True, blank=True)
    reponse = models.CharField(max_length=12, choices=REPONSES, blank=True)
    date_reponse = models.DateField(null=True, blank=True)
    reponse_detail = models.CharField(max_length=255, blank=True)
    historique = models.JSONField(default=list, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)
    tracer = DossierExpulsion.tracer

    class Meta:
        verbose_name = "Fiche d'hébergement d'urgence"
        verbose_name_plural = "Fiches d'hébergement d'urgence"
        ordering = ['-cree_le']

    def __str__(self):
        return f"{self.get_type_fiche_display()} – {self.dossier.numero}"

    @property
    def beneficiaire(self):
        return self.dossier.beneficiaire

    @property
    def mds(self):
        return self.dossier.mds

    @property
    def modifiable(self):
        return self.statut != self.ENVOYEE


class RappelHebergement(models.Model):
    """Texte d'un rappel de la note affiché en popup à l'ouverture de la fiche. Vide ou absent : texte par défaut.
    Décoché : le rappel n'est plus affiché."""
    CODES = [('OQTF', "OQTF"), ('PIECES', "Pièces d'identité (GED)"), ('AGDREF', "Numéro AGDREF"),
             ('SAS_SEUL', "DDETS uniquement par le SAS"), ('DROITS', "Droits ouverts (SAS)"),
             ('MECS', "MECS la Draille")]
    code = models.CharField(max_length=10, choices=CODES, unique=True)
    texte = models.TextField(blank=True, help_text="Texte affiché dans le popup. {sas} = adresse du SAS.")
    reference = models.CharField("Référence de la note", max_length=200, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Rappel de la note (popup)"
        verbose_name_plural = "Rappels de la note (popup)"
        ordering = ['code']

    def __str__(self):
        return self.get_code_display()

