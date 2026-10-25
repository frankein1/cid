# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/models/m_cap.py
"""
CAP - Chèques d'Accompagnement Personnalisé (chèques service Up,
catégorie « Alimentation, hygiène » uniquement ; les autres besoins passent par l'AFASE).

- ReceptionCAP : arrivage mensuel saisi par le régisseur de la MDS (douchette)
- TitreCAP     : un chèque = un numéro, suivi de l'entrée au coffre jusqu'à la remise
- DemandeCAP   : demande de l'AS → décision du cadre → remise → clôture (feuille signée)
- InventaireCAP: contrôle du coffre par le régisseur (scan de tout le stock physique)
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.mixins import AuditedMixin
from .m_generique import DemandeAide

VALEURS_CAP = (10, 20, 30)
VALEURS_CAP_CHOICES = [(v, f"{v} €") for v in VALEURS_CAP]


def est_regisseur(user, mds):
    """Régisseur de CETTE MDS (désigné sur la fiche MDS), ou administrateur."""
    if not user.is_authenticated or mds is None:
        return False
    return mds.regisseur_id == user.pk or user.a_la_capacite('peut_administrer')


class ReceptionCAP(AuditedMixin):
    """Arrivage de chèques service dans le coffre d'une MDS (bordereau mensuel)."""
    mds = models.ForeignKey('mds.MDS', on_delete=models.PROTECT, related_name='receptions_cap')
    regisseur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                  related_name='receptions_cap')
    date_reception = models.DateField(default=timezone.localdate)
    date_validite = models.DateField(help_text="Date de fin de validité imprimée sur les titres")
    reference = models.CharField(max_length=100, blank=True, help_text="N° du bordereau fournisseur (facultatif)")
    commentaire = models.TextField(blank=True)
    saisie_terminee = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date_reception', '-id']
        verbose_name = "Réception de chèques service"
        verbose_name_plural = "Réceptions de chèques service"

    def __str__(self):
        return f"Réception CAP {self.date_reception:%d/%m/%Y} - {self.mds}"

    @property
    def total(self):
        return sum(t.valeur for t in self.titres.all())


class TitreCAP(models.Model):
    """Un chèque service, identifié par son numéro (code-barres)."""
    STATUTS = [
        ('EN_STOCK', 'Au coffre'),
        ('REMIS', 'Remis'),
        ('PERDU', 'Perdu'),
        ('VOLE', 'Volé'),
        ('RETOURNE', 'Retourné au régisseur (périmé / annulé)'),
    ]
    numero = models.CharField(max_length=60, unique=True)
    valeur = models.PositiveSmallIntegerField(choices=VALEURS_CAP_CHOICES)
    reception = models.ForeignKey(ReceptionCAP, on_delete=models.PROTECT, related_name='titres')
    mds = models.ForeignKey('mds.MDS', on_delete=models.PROTECT, related_name='titres_cap')
    date_validite = models.DateField()
    statut = models.CharField(max_length=10, choices=STATUTS, default='EN_STOCK', db_index=True)

    # Remise
    demande = models.ForeignKey('AidFi.DemandeCAP', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='titres')
    date_remise = models.DateTimeField(null=True, blank=True)
    remis_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='titres_cap_remis')
    remis_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='titres_cap_recus', help_text="Agent (AS) qui a reçu les chèques")

    # Incident (perte, vol, retour)
    date_incident = models.DateTimeField(null=True, blank=True)
    incident_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='titres_cap_incidents')
    incident_commentaire = models.TextField(blank=True)

    date_entree = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date_validite', 'numero']
        verbose_name = "Titre CAP"
        verbose_name_plural = "Titres CAP"

    def __str__(self):
        return f"{self.numero} ({self.valeur} €)"

    @property
    def est_perime(self):
        return self.date_validite < timezone.localdate()


class DemandeCAP(DemandeAide):
    """Demande de chèques service (urgence, alimentation / hygiène)."""
    motivation = models.TextField(help_text="Situation et motivation de l'assistant(e) social(e)")
    remise_paierie = models.BooleanField(
        default=False, help_text="Remise exceptionnelle par la paierie départementale (Marseille)")

    # Décision
    montant_accorde = models.PositiveIntegerField(null=True, blank=True)
    decide_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='decisions_cap')
    date_decision = models.DateTimeField(null=True, blank=True)
    motif_refus = models.TextField(blank=True)

    # Remise
    date_remise = models.DateTimeField(null=True, blank=True)
    remis_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='remises_cap')
    remis_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='remises_cap_recues')
    numeros_paierie = models.TextField(blank=True, help_text="Numéros des titres remis par la paierie")
    reference_comptable = models.CharField("N° d'enregistrement comptable", max_length=60, blank=True,
                                           help_text="Saisi par la régie centrale (remise par la paierie)")

    # Clôture (feuille signée scannée)
    feuille_signee = models.ForeignKey('ged.DocumentGED', on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='+')
    date_cloture = models.DateTimeField(null=True, blank=True)
    cloture_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='clotures_cap')

    class Meta:
        verbose_name = "Demande CAP"
        verbose_name_plural = "Demandes CAP"

    def __str__(self):
        return f"CAP-{self.pk} – {self.beneficiaire}"

    def clean(self):
        if self.montant_sollicite and int(self.montant_sollicite) % 10:
            raise ValidationError({'montant_sollicite': "Le montant doit être un multiple de 10 €."})

    @property
    def total_remis(self):
        return sum(t.valeur for t in self.titres.all())


class InventaireCAP(AuditedMixin):
    """
    Inventaire du coffre par le régisseur, sans périodicité imposée :
    il scanne tous les chèques physiquement présents, CID compare au stock théorique.
    """
    mds = models.ForeignKey('mds.MDS', on_delete=models.PROTECT, related_name='inventaires_cap')
    regisseur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                  related_name='inventaires_cap')
    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    numeros = models.JSONField(default=list, blank=True, help_text="Numéros scannés au coffre")
    termine = models.BooleanField(default=False)
    resultat = models.JSONField(default=dict, blank=True, help_text="Photographie des écarts à la clôture")
    commentaire = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_debut']
        verbose_name = "Inventaire CAP"
        verbose_name_plural = "Inventaires CAP"

    def __str__(self):
        return f"Inventaire CAP {self.date_debut:%d/%m/%Y} - {self.mds}"

    @property
    def a_des_ecarts(self):
        r = self.resultat or {}
        return bool(r.get('manquants') or r.get('inattendus'))
