# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/models/m_referentiel.py
"""
Référentiel d'aide à la décision des AFASE et paramètres des aides financières.

Rien n'est écrit en dur dans le code : les seuils, montants indicatifs et conditions viennent de la note
de service en vigueur et sont saisis (ou importés) dans l'administration de CID. Tant qu'un paramètre
est vide, l'alerte ou l'indication correspondante n'est simplement pas affichée.
"""
from django.db import models


class ParametresAides(models.Model):
    """Paramètres uniques (une seule ligne) : seuils de la note de service en vigueur."""
    reference_note = models.CharField("Note de service en vigueur", max_length=200, blank=True,
                                      help_text="Ex. : numéro et date de la note.")
    seuil_montant_controle = models.DecimalField(
        "Montant au-delà duquel le contrôle UAGAF est renforcé (€)", max_digits=8, decimal_places=2,
        null=True, blank=True)
    seuil_nb_aides_12_mois = models.PositiveSmallIntegerField(
        "Nombre d'AFASE accordées sur 12 mois à partir duquel le contrôle est renforcé", null=True, blank=True)
    rav_seuil_accord = models.DecimalField(
        "Soutien alimentaire : reste à vivre en dessous duquel l'aide peut être accordée (€/jour/personne)",
        max_digits=6, decimal_places=2, null=True, blank=True)
    rav_seuil_parentalite = models.DecimalField(
        "Soutien alimentaire : reste à vivre au-dessus duquel l'aide relève seulement du soutien à la parentalité",
        max_digits=6, decimal_places=2, null=True, blank=True)
    participation_famille_pct = models.PositiveSmallIntegerField(
        "Participation minimale de la famille (%)", null=True, blank=True,
        help_text="Rappel affiché au cadre (sauf versement à un tiers, au centime près).")
    regie_montant_max = models.DecimalField(
        "Régie d'urgence : montant maximum (€)", max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Facultatif. Vide : seul le rappel « se conformer au maximum prévu par la note » s'affiche.")

    class Meta:
        verbose_name = "Paramètres des aides financières"
        verbose_name_plural = "Paramètres des aides financières"

    def __str__(self):
        return "Paramètres des aides financières" + (f" – {self.reference_note}" if self.reference_note else "")

    @classmethod
    def actuels(cls):
        return cls.objects.first() or cls()


class ReferentielMotifAFASE(models.Model):
    """Une ligne par motif d'accord (codes 1 à 13) : aides à mobiliser au préalable, conditions."""
    code = models.CharField("Code d'accord", max_length=2, unique=True)
    libelle = models.CharField("Motif", max_length=150)
    aides_prealables = models.TextField("Aides mobilisables au préalable", blank=True,
                                        help_text="Une aide par ligne : le travailleur social les coche.")
    conditions = models.TextField("Conditions d'attribution et montants indicatifs", blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ('id',)
        verbose_name = "Motif du référentiel AFASE"
        verbose_name_plural = "Référentiel d'aide à la décision AFASE"

    def __str__(self):
        return f"{self.code} – {self.libelle}"

    @property
    def liste_aides(self):
        return [l.strip(" -•\t") for l in self.aides_prealables.splitlines() if l.strip(" -•\t")]


class MontantIndicatifAFASE(models.Model):
    """Montant indicatif d'un motif, selon le nombre d'enfants ou un autre critère (niveau scolaire…)."""
    motif = models.ForeignKey(ReferentielMotifAFASE, on_delete=models.CASCADE, related_name='montants')
    critere = models.CharField("Critère", max_length=100, help_text="Ex. : « 2 enfants », « collège », « par enfant ».")
    nb_enfants = models.PositiveSmallIntegerField(
        "Nombre d'enfants", null=True, blank=True,
        help_text="Pour un montant selon le nombre d'enfants ; la plus grande valeur vaut « et plus ».")
    montant = models.DecimalField("Montant (€)", max_digits=8, decimal_places=2)
    par_mois = models.BooleanField("Par mois", default=True)

    class Meta:
        ordering = ('motif', 'nb_enfants', 'id')
        verbose_name = "Montant indicatif"

    def __str__(self):
        return f"{self.motif.code} – {self.critere} : {self.montant} €"
