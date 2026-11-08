# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/models/m_logement_social.py
from django.conf import settings
from django.db import models
from django.utils import timezone


# ==========================================================================
# DEMANDE DE LOGEMENT SOCIAL (numéro unique, DALO, mutation, Al'In)
# ==========================================================================

ETATS_DOSSIER = [('EN_COURS', "En cours"), ('ACCEPTE', "Accepté"), ('REFUSE', "Refusé")]
ETATS_ALIN = [('EN_COURS', "En cours"), ('EN_PROPOSITION', "En proposition"), ('REFUSE', "Refusé")]


class DemandeLogementSocial(models.Model):
    """Ce que la MDS sait de la demande de logement social de l'usager. Saisi à la main : la MDS n'aide aux
    démarches que ponctuellement (Maison France Services), mais le numéro et les dates servent au suivi, au DSF et
    à la commission des publics prioritaires."""
    beneficiaire = models.OneToOneField('beneficiaire.Beneficiaire', on_delete=models.CASCADE,
                                        related_name='demande_logement')
    nud = models.CharField("Numéro unique (NUD)", max_length=30, blank=True)
    date_creation = models.DateField("Date de création du NUD", null=True, blank=True)
    date_renouvellement = models.DateField("Dernier renouvellement", null=True, blank=True)
    dalo_depose = models.BooleanField("Recours DALO déposé", default=False)
    dalo_date = models.DateField("Date de dépôt du DALO", null=True, blank=True)
    dalo_etat = models.CharField("État du DALO", max_length=12, choices=ETATS_DOSSIER, blank=True)
    mutation_deposee = models.BooleanField("Demande de mutation déposée", default=False)
    mutation_date = models.DateField("Date de dépôt de la mutation", null=True, blank=True)
    mutation_etat = models.CharField("État de la mutation", max_length=12, choices=ETATS_DOSSIER, blank=True)
    alin_inscrit = models.BooleanField("Inscrit(e) sur Al'In", default=False)
    alin_date = models.DateField("Date d'inscription Al'In", null=True, blank=True)
    alin_etat = models.CharField("État Al'In", max_length=15, choices=ETATS_ALIN, blank=True)
    communes_souhaitees = models.JSONField(default=list, blank=True)
    typologie_souhaitee = models.CharField("Typologie souhaitée", max_length=20, blank=True)
    etage_souhaite = models.CharField("Étage", max_length=30, blank=True)
    pmr = models.BooleanField("Logement pour personne à mobilité réduite", default=False)
    precisions = models.TextField("Précisions", blank=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Demande de logement social"
        verbose_name_plural = "Demandes de logement social"

    def __str__(self):
        return f"Demande de logement de {self.beneficiaire} ({self.nud or 'sans NUD'})"

    def anciennete(self, aujourdhui=None):
        """« 3 ans et 2 mois » depuis la création du NUD."""
        if not self.date_creation:
            return ""
        j = aujourdhui or timezone.localdate()
        mois = (j.year - self.date_creation.year) * 12 + j.month - self.date_creation.month - (j.day < self.date_creation.day)
        ans, mois = divmod(max(mois, 0), 12)
        morceaux = ([f"{ans} an{'s' if ans > 1 else ''}"] if ans else []) + ([f"{mois} mois"] if mois else [])
        return " et ".join(morceaux) or "moins d'un mois"

    def prochain_renouvellement(self):
        """La demande se renouvelle chaque année, à la date anniversaire de sa création."""
        base = self.date_renouvellement or self.date_creation
        if not base:
            return None
        j = timezone.localdate()
        d = base
        while d <= j:
            try:
                d = d.replace(year=d.year + 1)
            except ValueError:                     # 29 février
                d = d.replace(year=d.year + 1, day=28)
        return d

    @property
    def alerte_renouvellement(self):
        prochain = self.prochain_renouvellement()
        return bool(prochain and (prochain - timezone.localdate()).days <= 30)
