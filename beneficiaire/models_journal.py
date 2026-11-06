# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/models_journal.py
"""Journal de l'accompagnement : référentiel des types d'accompagnement et entretiens sociaux.
Repris de la conception de Mon Suivi Social (types avec case « légal », synthèse et synthèse privée), réécrit pour CID."""
from django.conf import settings
from django.db import models
from django.utils import timezone

from core.mixins import AuditedMixin


class TypeAccompagnement(models.Model):
    code = models.SlugField(max_length=40, unique=True)
    libelle = models.CharField("Libellé", max_length=120)
    legal = models.BooleanField("Accompagnement légal", default=False,
                                help_text="Accompagnement prévu par un texte (RSA, protection de l'enfance, MASP…) : "
                                          "signalé dans le journal et compté à part.")
    description = models.TextField(blank=True)
    ordre = models.PositiveSmallIntegerField(default=100)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Type d'accompagnement"
        verbose_name_plural = "Types d'accompagnement"
        ordering = ['ordre', 'libelle']

    def __str__(self):
        return self.libelle + (" (légal)" if self.legal else "")


class EntretienSocial(AuditedMixin):
    ACCUEIL, RDV, VAD, TELEPHONE, ECRIT, VISIO, EXTERIEUR = 'ACCUEIL', 'RDV', 'VAD', 'TELEPHONE', 'ECRIT', 'VISIO', 'EXTERIEUR'
    MODES = [(ACCUEIL, "Accueil sans rendez-vous"), (RDV, "Rendez-vous à la MDS"), (VAD, "Visite à domicile"),
             (TELEPHONE, "Téléphone"), (ECRIT, "Courriel ou courrier"), (VISIO, "Visioconférence"),
             (EXTERIEUR, "À l'extérieur (partenaire, audience…)")]

    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE, related_name='entretiens')
    date = models.DateField(default=timezone.localdate)
    heure = models.TimeField(null=True, blank=True)
    mode = models.CharField(max_length=10, choices=MODES, default=RDV)
    duree_minutes = models.PositiveSmallIntegerField("Durée (minutes)", null=True, blank=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='entretiens_rediges')
    co_intervenants = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='entretiens_co',
                                             verbose_name="Co-intervenants")
    personnes_presentes = models.ManyToManyField('beneficiaire.Beneficiaire', blank=True, related_name='+',
                                                 verbose_name="Autres personnes du foyer présentes")
    types = models.ManyToManyField(TypeAccompagnement, blank=True, related_name='entretiens',
                                   verbose_name="Types d'accompagnement")
    objet = models.CharField(max_length=150)
    synthese = models.TextField("Synthèse", blank=True,
                                help_text="Visible des agents qui ont accès au dossier complet. Des faits, pas de jugement.")
    synthese_privee = models.TextField("Synthèse privée", blank=True,
                                       help_text="Notes de travail lisibles par vous seul(e).")
    suite_a_donner = models.CharField("Suite à donner", max_length=255, blank=True)
    echeance = models.DateField("Échéance", null=True, blank=True)
    suite_faite = models.BooleanField("Suite faite", default=False)
    orientation = models.ForeignKey('partenaires.Partenaire', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='+', verbose_name="Orientation vers un partenaire")
    orientation_precision = models.CharField("Précision sur l'orientation", max_length=255, blank=True)
    creneau = models.ForeignKey('planning.CreneauRdv', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='entretiens', verbose_name="Rendez-vous")

    class Meta:
        verbose_name = "Entretien"
        verbose_name_plural = "Entretiens"
        ordering = ['-date', '-heure', '-pk']

    def __str__(self):
        return f"{self.date:%d/%m/%Y} – {self.objet}"

    @property
    def legal(self):
        return any(t.legal for t in self.types.all())

    def peut_lire_prive(self, user):
        return user.is_authenticated and user.pk == self.auteur_id

    def peut_modifier(self, user):
        return user.is_authenticated and (user.pk == self.auteur_id or user.is_superuser)
