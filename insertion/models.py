# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/models.py
"""
Module RSA – Insertion, étape 1 : pôles insertion et référentiel des actions d'insertion.

- Un pôle insertion couvre plusieurs MDS ; ses agents (administratif, cadre, médecin) n'ont accès qu'au module RSA.
- Le référentiel a deux niveaux : actions départementales (base : programme départemental d'insertion), gérées
  par les pôles et l'administration, et actions locales créées par une MDS. Chaque action est rattachée à un
  type commun, pour des statistiques comparables entre MDS.
Aucun contenu interne au Département n'est écrit dans le code : la liste des actions s'importe en CSV.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class PoleInsertion(models.Model):
    code = models.CharField("Code", max_length=30, unique=True, help_text="Ex. : PI-IX")
    nom = models.CharField("Nom", max_length=200)
    adresse = models.CharField("Adresse", max_length=255, blank=True)
    code_postal = models.CharField("Code postal", max_length=10, blank=True)
    ville = models.CharField("Ville", max_length=100, blank=True)
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    email = models.EmailField("Courriel", blank=True)
    email_mssante_medecin = models.EmailField(
        "Adresse MSSanté du médecin du pôle", blank=True,
        help_text="Messagerie sécurisée de santé : les médecins traitants y envoient les certificats médicaux "
                  "des contrats santé. Vide : envoi sous pli cacheté.")
    mds = models.ManyToManyField('mds.MDS', blank=True, related_name='poles_insertion', verbose_name="MDS rattachées")
    membres = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='poles_insertion',
                                     verbose_name="Agents du pôle",
                                     help_text="Les droits viennent de leurs profils (administratif, cadre ou médecin du pôle).")
    actif = models.BooleanField("Actif", default=True)

    class Meta:
        verbose_name = "Pôle insertion"
        verbose_name_plural = "Pôles insertion"
        ordering = ['code']

    def __str__(self):
        return self.nom


class TypeActionInsertion(models.Model):
    """Typologie commune à toutes les MDS (réglable en administration ; désactiver plutôt que supprimer)."""
    code = models.SlugField("Code", max_length=40, unique=True)
    libelle = models.CharField("Libellé", max_length=150)
    ordre = models.PositiveSmallIntegerField("Ordre", default=100)
    actif = models.BooleanField("Actif", default=True)

    class Meta:
        verbose_name = "Type d'action d'insertion"
        verbose_name_plural = "Types d'actions d'insertion"
        ordering = ['ordre', 'libelle']

    def __str__(self):
        return self.libelle


class ActionInsertion(models.Model):
    DEPARTEMENTAL, LOCAL = 'DEPARTEMENTAL', 'LOCAL'
    NIVEAUX = [(DEPARTEMENTAL, "Départementale"), (LOCAL, "Locale (MDS)")]

    code = models.CharField("Code", max_length=40, help_text="Code court propre à CID, ex. : ACCGLO")
    libelle = models.CharField("Libellé", max_length=200)
    type_action = models.ForeignKey(TypeActionInsertion, on_delete=models.PROTECT, related_name='actions',
                                    verbose_name="Type d'action")
    niveau = models.CharField("Niveau", max_length=15, choices=NIVEAUX, default=DEPARTEMENTAL)
    mds = models.ForeignKey('mds.MDS', on_delete=models.CASCADE, null=True, blank=True, related_name='actions_insertion',
                            verbose_name="MDS", help_text="Actions locales seulement.")
    poles = models.ManyToManyField(PoleInsertion, blank=True, related_name='actions', verbose_name="Pôles concernés",
                                   help_text="Vide : tout le département.")
    territoire = models.CharField("Territoire", max_length=255, blank=True,
                                  help_text="Communes ou quartiers, si l'action ne couvre pas tout le périmètre.")
    porteur = models.CharField("Porteur", max_length=200, blank=True)
    partenaire = models.ForeignKey('partenaires.Partenaire', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='actions_insertion', verbose_name="Porteur dans l'annuaire")
    public_vise = models.TextField("Public visé", blank=True)
    description = models.TextField("Description", blank=True)
    duree = models.CharField("Durée ou volume", max_length=100, blank=True, help_text="Ex. : 3 mois, 18 mois au plus, 252 h")
    destinataires = models.TextField("Destinataires de la prescription", blank=True,
                                     help_text="Une adresse par ligne (porteur, pôle insertion en copie…).")
    pieces_a_joindre = models.TextField("Pièces à joindre", blank=True, help_text="Une pièce par ligne.")
    comite_suivi = models.BooleanField("Passage en comité de suivi technique", default=False)
    rythme_comite = models.CharField("Rythme des comités", max_length=100, blank=True, help_text="Ex. : semestriel")
    aussi_logement = models.BooleanField("Concerne aussi le logement", default=False)
    actif = models.BooleanField("Active", default=True)
    modifie_le = models.DateTimeField("Modifiée le", auto_now=True)
    modifie_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='+', verbose_name="Modifiée par")

    class Meta:
        verbose_name = "Action d'insertion"
        verbose_name_plural = "Actions d'insertion"
        ordering = ['type_action__ordre', 'libelle']
        constraints = [
            models.UniqueConstraint(fields=['code'], condition=Q(mds__isnull=True), name='action_insertion_code_dep'),
            models.UniqueConstraint(fields=['code', 'mds'], name='action_insertion_code_mds'),
        ]

    def __str__(self):
        return f"{self.libelle} ({self.code})"

    def clean(self):
        if self.niveau == self.LOCAL and not self.mds_id:
            raise ValidationError({'mds': "Une action locale est rattachée à une MDS."})
        if self.niveau == self.DEPARTEMENTAL and self.mds_id:
            raise ValidationError({'mds': "Une action départementale n'est pas rattachée à une MDS."})

    @property
    def liste_destinataires(self):
        return [l.strip() for l in self.destinataires.splitlines() if l.strip()]

    @property
    def liste_pieces(self):
        return [l.strip() for l in self.pieces_a_joindre.splitlines() if l.strip()]

    @property
    def perimetre(self):
        if self.niveau == self.LOCAL:
            return f"{self.mds.nom}" + (f" – {self.territoire}" if self.territoire else "")
        poles = ", ".join(p.nom for p in self.poles.all())
        base = poles or "Tout le département"
        return base + (f" – {self.territoire}" if self.territoire else "")
