# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/models/m_indigne.py
from django.conf import settings
from django.db import models
from django.utils import timezone

from .m_fsl import DemandeFSL


# ==========================================================================
# LUTTE CONTRE LE LOGEMENT INDIGNE (signalement au PDLHI)
# ==========================================================================

class SignalementHabitatIndigne(models.Model):
    BROUILLON, ENVOYE, CLOS = 'BROUILLON', 'ENVOYE', 'CLOS'
    STATUTS = [(BROUILLON, "En préparation"), (ENVOYE, "Envoyé au PDLHI"), (CLOS, "Clos")]
    ORIGINES = [('VAD', "Visite à domicile du TS"), ('LOCATAIRE', "Signalement du locataire"),
                ('BAILLEUR', "Signalement du bailleur"), ('COMMUNE', "Signalement de la commune"),
                ('AUTRE', "Autre")]

    # Lien à l'usager facultatif (recommandé quand il existe) : hors suivi MDS, le courrier est renvoyé au CIAS/CCAS
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='signalements_indigne')
    mds = models.ForeignKey('mds.MDS', on_delete=models.PROTECT, related_name='signalements_indigne')
    origine = models.CharField(max_length=12, choices=ORIGINES, default='VAD')
    statut = models.CharField(max_length=12, choices=STATUTS, default=BROUILLON)
    donnees = models.JSONField(default=dict, blank=True, help_text="Rubriques 1 à 8 de la fiche PDLHI")

    # Permis de louer : deux cases indépendantes (ville soumise / logement soumis)
    date_saisine = models.DateField("Date de saisine de la MDS", null=True, blank=True)
    permis_ville = models.BooleanField("Ville soumise au permis de louer", default=False)
    permis_logement = models.BooleanField("Logement soumis au permis de louer", default=False)

    # Rapport de visite à domicile : signé par le TS
    rapport_vad = models.TextField("Rapport de VAD", blank=True)
    vad_signee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='vad_signees_indigne')
    vad_date_signature = models.DateTimeField(null=True, blank=True)

    # Rapport de VAD relié au rendez-vous du planning et à l'entretien du journal de l'usager (dossier usager)
    creneau = models.ForeignKey('planning.CreneauRdv', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='signalements_indigne', verbose_name="Visite (rendez-vous du planning)")
    entretien = models.ForeignKey('beneficiaire.EntretienSocial', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='signalements_indigne', verbose_name="Entrée du journal")

    # Fiche PDLHI : signée par le cadre (responsable de la MDS)
    fiche_signee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='fiches_signees_indigne')
    fiche_date_signature = models.DateTimeField(null=True, blank=True)

    # Suivi après envoi
    date_envoi = models.DateField("Date d'envoi au PDLHI", null=True, blank=True)
    reponse_pdlhi = models.TextField("Réponse du PDLHI", blank=True)
    enquete_salubrite = models.BooleanField("Enquête de salubrité", default=False)
    suite = models.TextField("Suite donnée", blank=True)
    bascule_dalo = models.BooleanField("Bascule sur dispositif DALO", default=False)

    historique = models.JSONField(default=list, blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name='signalements_indigne_crees')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Signalement d'habitat indigne"
        verbose_name_plural = "Signalements d'habitat indigne"
        ordering = ['-date_creation']

    def __str__(self):
        cible = str(self.beneficiaire) if self.beneficiaire else "hors suivi"
        return f"Signalement indigne – {cible} ({self.get_statut_display()})"

    @property
    def modifiable(self):
        return self.statut == self.BROUILLON

    @property
    def fiche_signee(self):
        return self.fiche_signee_par_id is not None

    @property
    def vad_signee(self):
        return self.vad_signee_par_id is not None

    tracer = DemandeFSL.tracer
