# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/models/m_asell.py
"""Orientation ASELL (accompagnement socio-éducatif lié au logement) : fiche d'orientation généraliste ou renforcée,
volet accès ou maintien, adressée à un opérateur conventionné. La liste des opérateurs (territoires, actions) est
importée en administration."""
from django.conf import settings
from django.db import models

from .m_expulsion import DossierExpulsion


class OperateurASELL(models.Model):
    """Une ligne de la liste annuelle des opérateurs conventionnés (accompagnement social lié au FSL) : un opérateur,
    une antenne, une action (ASELL généraliste, renforcé, diagnostic courte durée, ateliers, auto-réhabilitation), un
    territoire. La liste se charge en administration (import du tableau du Département) : rien de local dans le code.
    Un nouvel import désactive l'ancienne liste sans l'effacer (les fiches déjà envoyées gardent leur opérateur)."""
    ASELL, ASC, ALL = 'ASELL', 'ASC', 'ALL'
    NATURES = [(ASELL, "ASELL (accompagnement individuel)"), (ASC, "ASC (action collective)"),
               (ALL, "ALL (auto-réhabilitation)")]
    GENERALISTE, RENFORCE, COURTE_DUREE = 'GENERALISTE', 'RENFORCE', 'COURTE_DUREE'
    ATELIERS, AUTO_REHABILITATION = 'ATELIERS', 'AUTO_REHAB'
    THEMATIQUES = [(GENERALISTE, "Généraliste"), (RENFORCE, "Renforcé"), (COURTE_DUREE, "Diagnostic courte durée"),
                   (ATELIERS, "Ateliers recherche logement"), (AUTO_REHABILITATION, "Auto-réhabilitation accompagnée")]

    sigle = models.CharField(max_length=60)
    nom = models.CharField(max_length=150)
    adresse = models.CharField(max_length=255, blank=True)
    cp_ville = models.CharField("Code postal et ville", max_length=100, blank=True)
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    emails = models.CharField("Adresses mail", max_length=255, blank=True,
                              help_text="Une ou plusieurs, séparées par des virgules : toutes sont proposées à l'envoi.")
    nature = models.CharField(max_length=5, choices=NATURES, default=ASELL)
    thematique = models.CharField("Thématique", max_length=12, choices=THEMATIQUES, default=GENERALISTE)
    territoire = models.TextField(blank=True, help_text="Tel qu'écrit dans la liste : communes, « 13e et 14e "
                                                        "arrondissements de Marseille », « Département »…")
    public_specifique = models.CharField("Public spécifique", max_length=255, blank=True)
    annee = models.PositiveSmallIntegerField("Année de la convention", null=True, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Opérateur conventionné (ASELL)"
        verbose_name_plural = "Opérateurs conventionnés (ASELL)"
        ordering = ['sigle', 'thematique', 'pk']

    def __str__(self):
        return f"{self.sigle} – {self.nom}" if self.nom and self.nom.upper() != self.sigle.upper() else self.sigle

    @property
    def ville(self):
        import re
        v = re.sub(r"^\s*\d{5}\s*", "", self.cp_ville or "")
        return re.sub(r"\s*CEDEX.*$", "", v, flags=re.I).strip().title()

    @property
    def liste_emails(self):
        import re
        return re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", self.emails or "")


class OrientationASELL(models.Model):
    GENERALISTE, RENFORCE = 'GENERALISTE', 'RENFORCE'
    TYPES = [(GENERALISTE, "ASELL généraliste"), (RENFORCE, "ASELL renforcé")]
    ACCES, MAINTIEN = 'ACCES', 'MAINTIEN'
    VOLETS = [(ACCES, "Accès"), (MAINTIEN, "Maintien")]
    BROUILLON, ENVOYEE, ABANDONNEE = 'BROUILLON', 'ENVOYEE', 'ABANDONNEE'
    STATUTS = [(BROUILLON, "En préparation"), (ENVOYEE, "Envoyée"), (ABANDONNEE, "Abandonnée")]
    ACCORD, ATTENTE, REFUS = 'ACCORD', 'ATTENTE', 'REFUS'
    REPONSES = [(ACCORD, "Mesure engagée"), (ATTENTE, "Liste d'attente"), (REFUS, "Orientation non retenue")]

    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE, related_name='orientations_asell')
    mds = models.ForeignKey('mds.MDS', on_delete=models.PROTECT, related_name='orientations_asell')
    dossier_expulsion = models.ForeignKey(DossierExpulsion, null=True, blank=True, on_delete=models.SET_NULL,
                                          related_name='orientations_asell')
    type_mesure = models.CharField(max_length=12, choices=TYPES, default=GENERALISTE)
    volet = models.CharField(max_length=8, choices=VOLETS, default=MAINTIEN)
    operateur = models.ForeignKey(OperateurASELL, null=True, blank=True, on_delete=models.SET_NULL, related_name='orientations')
    operateur_libre = models.CharField("Autre opérateur", max_length=150, blank=True)
    donnees = models.JSONField(default=dict, blank=True)
    statut = models.CharField(max_length=10, choices=STATUTS, default=BROUILLON)
    date_envoi = models.DateField(null=True, blank=True)
    reponse = models.CharField(max_length=8, choices=REPONSES, blank=True)
    date_reponse = models.DateField(null=True, blank=True)
    reponse_detail = models.CharField(max_length=255, blank=True)
    historique = models.JSONField(default=list, blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)
    tracer = DossierExpulsion.tracer

    class Meta:
        verbose_name = "Orientation ASELL"
        verbose_name_plural = "Orientations ASELL"
        ordering = ['-cree_le']

    def __str__(self):
        return f"{self.get_type_mesure_display()} ({self.get_volet_display().lower()}) – {self.beneficiaire}"

    @property
    def nom_operateur(self):
        return str(self.operateur) if self.operateur else self.operateur_libre

    @property
    def modifiable(self):
        return self.statut == self.BROUILLON
