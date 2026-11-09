# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/models/m_asell.py
"""Orientation ASELL (accompagnement socio-éducatif lié au logement) : fiche d'orientation généraliste ou renforcée,
volet accès ou maintien, adressée à un opérateur. Les opérateurs et leurs adresses sont réglés en administration."""
from django.conf import settings
from django.db import models

from .m_expulsion import DossierExpulsion


class OperateurASELL(models.Model):
    """Destinataire des fiches : opérateur de la mesure, ou service qui les centralise (réglé en administration)."""
    nom = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    territoire = models.CharField(max_length=150, blank=True)
    generaliste = models.BooleanField("ASELL généraliste", default=True)
    renforce = models.BooleanField("ASELL renforcé", default=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Opérateur ASELL (destinataire des fiches)"
        verbose_name_plural = "Opérateurs ASELL (destinataires des fiches)"
        ordering = ['nom']

    def __str__(self):
        return self.nom


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
