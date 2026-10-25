# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# partenaires/models.py
"""
Annuaire des partenaires, COMMUN à toutes les MDS (CMP, bailleurs, CCAS, écoles, France Travail…).
Contacts professionnels uniquement. On désactive un partenaire, on ne le supprime pas :
l'historique des rendez-vous qui le citent est conservé.
"""
from django.conf import settings
from django.db import models

THEMATIQUES = [
    ('LOGEMENT', "Logement"),
    ('SANTE', "Santé"),
    ('EMPLOI', "Emploi, insertion"),
    ('SCOLARITE', "Scolarité, éducation"),
    ('ENFANCE', "Enfance, famille"),
    ('HANDICAP', "Handicap, autonomie"),
    ('BUDGET', "Budget, surendettement"),
    ('JUSTICE', "Justice"),
    ('ACCES_DROITS', "Accès aux droits"),
    ('AUTRE', "Autre"),
]


class Partenaire(models.Model):
    organisme = models.CharField(max_length=150, help_text="Ex. : CMP de Martigues, 13 Habitat, CCAS de Port-de-Bouc")
    service = models.CharField(max_length=150, blank=True)
    thematique = models.CharField(max_length=20, choices=THEMATIQUES, default='AUTRE')
    civilite = models.CharField(max_length=5, choices=[('M.', 'M.'), ('MME', 'Mme')], blank=True)
    nom_contact = models.CharField("Nom du contact", max_length=80, blank=True)
    prenom_contact = models.CharField("Prénom du contact", max_length=80, blank=True)
    fonction = models.CharField(max_length=120, blank=True)
    email = models.EmailField("E-mail", blank=True)
    telephone = models.CharField("Téléphone", max_length=20, blank=True)
    adresse = models.CharField(max_length=200, blank=True)
    code_postal = models.CharField(max_length=5, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    commentaire = models.TextField(blank=True, help_text="Horaires, modalités de contact…")

    actif = models.BooleanField(default=True)
    mds_origine = models.ForeignKey('mds.MDS', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='+', help_text="MDS qui a créé la fiche (pour information)")
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    modifie_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name='+')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organisme', 'nom_contact']
        verbose_name = "Partenaire"
        indexes = [models.Index(fields=['actif', 'organisme'])]

    def __str__(self):
        contact = self.contact
        return f"{self.organisme}{' – ' + contact if contact else ''}"

    @property
    def contact(self):
        return " ".join(x for x in (self.prenom_contact, self.nom_contact.upper() if self.nom_contact else "") if x)

    def peut_etre_modifie_par(self, user):
        """Tout agent peut ajouter un partenaire ; seuls son auteur et les cadres le modifient."""
        return user.is_authenticated and (user.is_superuser or user.pk == self.cree_par_id
                                          or user.a_la_capacite('peut_valider'))
