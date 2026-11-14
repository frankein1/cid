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
    thematiques_inclusion = models.JSONField(
        "Thématiques data·inclusion", default=list, blank=True,
        help_text="Catégories du référentiel national (ex. « logement-hebergement ») proposées pour chercher un service "
                  "d'orientation à partir de ce type.")

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
        """Synthèse privée : son auteur, et le référent actuel de l'usager en reprise (lecture seule)."""
        if not user.is_authenticated:
            return False
        return user.pk == self.auteur_id or self.beneficiaire.referent_mds_id == user.pk

    def peut_modifier(self, user):
        return user.is_authenticated and (user.pk == self.auteur_id or user.is_superuser)


class NotePersonnelle(models.Model):
    """Note datée d'un travailleur social sur un usager (prise de notes de travail). Privée à son auteur ; le
    travailleur social décide, note par note, si elle suit le dossier à la MDS d'accueil lors d'un transfert.
    L'auteur peut la supprimer à tout moment, transfert ou non."""
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE, related_name='notes_personnelles')
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='notes_personnelles')
    date_note = models.DateTimeField("Date et heure", default=timezone.now)
    contenu = models.TextField("Note")
    a_transmettre = models.BooleanField(
        "Suit le dossier en cas de transfert", default=False,
        help_text="Si coché, la note est transmise à la MDS d'accueil lors d'un transfert de l'usager.")
    transmise_a_mds = models.ForeignKey('mds.MDS', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='notes_transmises', verbose_name="Transmise à la MDS")
    transmise_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_note', '-pk']
        verbose_name = "Note personnelle"
        verbose_name_plural = "Notes personnelles"

    def __str__(self):
        return f"Note du {self.date_note:%d/%m/%y %H:%M} sur {self.beneficiaire}"

    def peut_lire(self, user):
        """L'auteur ; le référent actuel de l'usager en reprise (lecture seule) ; et, une fois transmise,
        les agents de la MDS destinataire."""
        if not user.is_authenticated:
            return False
        if self.auteur_id == user.pk:
            return True
        if self.beneficiaire.referent_mds_id == user.pk:
            return True
        if not self.transmise_a_mds_id:
            return False
        from mds.models import UserMDSProfile
        return UserMDSProfile.objects.filter(user=user, mds_id=self.transmise_a_mds_id, actif=True).exists()

    def peut_gerer(self, user):
        """Modifier le choix de transmission ou supprimer : l'auteur seul."""
        return user.is_authenticated and self.auteur_id == user.pk
