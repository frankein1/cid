# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

"""
# AidFi/models/m_regie.py
Modèles RÉGIE D'URGENCE
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings  # ✅ AJOUTÉ
from .m_generique import DemandeAide

class RegieUrgence(models.Model):
    demande = models.OneToOneField(DemandeAide, on_delete=models.CASCADE, related_name='regie_urgence')
    montant_urgence = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)])
    motif_urgence = models.TextField()
    date_rendez_vous_regie = models.DateTimeField(null=True, blank=True)
    regisseur = models.CharField(max_length=200, blank=True)
    
    date_versement = models.DateTimeField(null=True, blank=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # ✅ settings.AUTH_USER_MODEL
        on_delete=models.SET_NULL, 
        null=True,
        related_name='regies_creees')  # ✅ AJOUTÉ


# =============================================================================
# RÉGIE D'URGENCE – circuit complet (sur le modèle des CAP)
#   AS propose → cadre décide → régie centrale (paierie) verse sous 24 h → clôture
#   Versement en espèces (le plus souvent) ou paiement à un tiers (ex. dette d'hôtel :
#   facture et RIB du tiers joints, montant éventuellement partiel).
# =============================================================================

DELAI_VERSEMENT_HEURES = 24


class DemandeRegie(DemandeAide):
    MODES = [("ESPECES", "En espèces à l'usager"), ("TIERS", "Paiement à un tiers (hôtel, fournisseur…)")]

    motivation = models.TextField(help_text="Situation et motif de l'urgence")
    mode_paiement = models.CharField("Mode de paiement", max_length=10, choices=MODES, default="ESPECES")
    tiers_nom = models.CharField("Tiers à payer", max_length=150, blank=True)
    tiers_reference = models.CharField("Référence de la facture", max_length=60, blank=True)

    # Décision
    montant_accorde = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    decide_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='decisions_regie')
    date_decision = models.DateTimeField(null=True, blank=True)
    motif_refus = models.TextField(blank=True)

    # Versement par la régie centrale
    date_versement = models.DateTimeField(null=True, blank=True)
    montant_verse = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    verse_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='versements_regie')
    reference_comptable = models.CharField("N° d'enregistrement comptable", max_length=60, blank=True)

    class Meta:
        verbose_name = "Demande de régie d'urgence"
        verbose_name_plural = "Demandes de régie d'urgence"

    def __str__(self):
        return f"REGIE-{self.pk} – {self.beneficiaire.nom}"

    @property
    def heures_depuis_decision(self):
        from django.utils import timezone
        if not self.date_decision:
            return None
        fin = self.date_versement or timezone.now()
        return round((fin - self.date_decision).total_seconds() / 3600, 1)

    @property
    def en_retard(self):
        """Versement attendu sous 24 h après l'accord."""
        h = self.heures_depuis_decision
        return h is not None and h > DELAI_VERSEMENT_HEURES and self.statut in ('TRANSMISE_PAIERIE', 'CLOTUREE')
