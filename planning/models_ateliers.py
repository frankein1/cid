# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/models_ateliers.py
"""
Ateliers collectifs (conception reprise de Mon Suivi Social v2, ANCT, licence MIT) : un atelier (« Budget »,
« Parentalité », « Numérique »…) a des séances datées, avec un nombre de places, une éventuelle condition
d'âge, une participation payante ou non, une liste principale et une liste d'attente, et les présences.
Les participants sont des usagers de CID ou des personnes extérieures. Une séance peut être rattachée à une
action d'insertion (insertion.ActionInsertion). Services : planning/ateliers.py.
"""
from django.conf import settings
from django.db import models


class Atelier(models.Model):
    """Thème d'atelier, propre à une MDS ou commun au département (mds vide)."""
    nom = models.CharField(max_length=120)
    mds = models.ForeignKey('mds.MDS', on_delete=models.CASCADE, null=True, blank=True, related_name='ateliers',
                            help_text="Vide : atelier proposé dans tout le département")
    description = models.TextField(blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom']
        unique_together = ('nom', 'mds')
        verbose_name = "Atelier collectif"
        verbose_name_plural = "Ateliers collectifs"

    def __str__(self):
        return self.nom


class SeanceAtelier(models.Model):
    PLUS_DE, MOINS_DE = 'PLUS_DE', 'MOINS_DE'
    CONDITIONS_AGE = [(PLUS_DE, "à partir de"), (MOINS_DE, "jusqu'à")]
    PREVUE, ANNULEE = 'PREVUE', 'ANNULEE'
    STATUTS = [(PREVUE, "Prévue"), (ANNULEE, "Annulée")]

    atelier = models.ForeignKey(Atelier, on_delete=models.PROTECT, related_name='seances')
    mds = models.ForeignKey('mds.MDS', on_delete=models.CASCADE, related_name='seances_ateliers')
    intitule = models.CharField("Intitulé de la séance", max_length=150, blank=True)
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    lieu = models.CharField(max_length=150, blank=True, help_text="Vide : à la MDS")
    animateur = models.CharField(max_length=120, blank=True)
    partenaire = models.ForeignKey('partenaires.Partenaire', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='seances_ateliers', help_text="Partenaire qui co-anime")
    action_insertion = models.ForeignKey('insertion.ActionInsertion', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='seances_ateliers',
                                         help_text="Action d'insertion correspondante (RSA)")
    description = models.TextField(blank=True)
    places = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Vide : sans limite")
    condition_age = models.CharField(max_length=10, choices=CONDITIONS_AGE, blank=True)
    age_limite = models.PositiveSmallIntegerField(null=True, blank=True)
    payant = models.BooleanField(default=False)
    tarif = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    statut = models.CharField(max_length=10, choices=STATUTS, default=PREVUE)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'heure_debut']
        verbose_name = "Séance d'atelier"
        verbose_name_plural = "Séances d'ateliers"

    def __str__(self):
        return f"{self.atelier} – {self.date:%d/%m/%Y}"

    @property
    def titre(self):
        return f"{self.atelier}{f' : {self.intitule}' if self.intitule else ''}"

    def inscrits(self):
        return self.participants.filter(liste=ParticipantAtelier.PRINCIPALE)

    def attente(self):
        return self.participants.filter(liste=ParticipantAtelier.ATTENTE).order_by('date_inscription', 'pk')

    @property
    def places_restantes(self):
        if self.places is None:
            return None
        return max(0, self.places - self.inscrits().count())

    @property
    def condition_age_texte(self):
        if not self.condition_age or self.age_limite is None:
            return ""
        return f"{self.get_condition_age_display()} {self.age_limite} ans"


class ParticipantAtelier(models.Model):
    USAGER, EXTERNE, ACCOMPAGNANT = 'USAGER', 'EXTERNE', 'ACCOMPAGNANT'
    TYPES = [(USAGER, "Usager CID"), (EXTERNE, "Personne extérieure"), (ACCOMPAGNANT, "Accompagnant")]
    PRINCIPALE, ATTENTE = 'PRINCIPALE', 'ATTENTE'
    LISTES = [(PRINCIPALE, "Inscrit"), (ATTENTE, "Liste d'attente")]
    VENU, ABSENT, EXCUSE = 'VENU', 'ABSENT', 'EXCUSE'
    PRESENCES = [(VENU, "Présent"), (ABSENT, "Absent"), (EXCUSE, "Excusé")]

    seance = models.ForeignKey(SeanceAtelier, on_delete=models.CASCADE, related_name='participants')
    type = models.CharField(max_length=12, choices=TYPES, default=USAGER)
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='participations_ateliers')
    # personne extérieure (ou accompagnant) : le strict nécessaire
    prenom = models.CharField(max_length=60, blank=True)
    nom = models.CharField(max_length=60, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    ville = models.CharField(max_length=100, blank=True)
    liste = models.CharField(max_length=10, choices=LISTES, default=PRINCIPALE)
    presence = models.CharField(max_length=8, choices=PRESENCES, blank=True)
    paiement_recu = models.BooleanField(default=False)
    montant = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    commentaire = models.CharField(max_length=255, blank=True)
    inscrit_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    date_inscription = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['liste', 'date_inscription', 'pk']
        verbose_name = "Participant à un atelier"
        verbose_name_plural = "Participants aux ateliers"
        constraints = [models.UniqueConstraint(fields=['seance', 'beneficiaire'], condition=models.Q(beneficiaire__isnull=False),
                                               name='atelier_usager_unique')]

    def __str__(self):
        return self.nom_complet

    @property
    def nom_complet(self):
        if self.beneficiaire_id:
            return f"{self.beneficiaire.nom.upper()} {self.beneficiaire.prenom}"
        return f"{self.nom.upper()} {self.prenom}".strip()
