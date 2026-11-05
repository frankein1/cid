# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/models.py
"""
Situation d'un usager auprès des organismes (CAF/MSA, France Travail), rapatriée
par l'API Particulier. Une ligne par usager et par source, mise à jour à chaque
actualisation ; chaque appel est en plus tracé dans le journal (qui, quand, quoi).

Minimisation des données : on ne garde que l'utile pour l'accompagnement
(droit ouvert, date, montant du QF, catégorie d'inscription), jamais les
adresses ni les coordonnées renvoyées par les organismes.
"""
from django.conf import settings
from django.db import models


SOURCES = [
    ('RSA', "RSA"),
    ('PRIME_ACTIVITE', "Prime d'activité"),
    ('QUOTIENT_FAMILIAL', "Quotient familial CAF / MSA"),
    ('ASF', "Allocation de soutien familial"),
    ('AAH', "Allocation adulte handicapé"),
    ('C2S', "Complémentaire santé solidaire"),
    ('FRANCE_TRAVAIL', "Inscription France Travail"),
]

STATUTS_APPEL = [
    ('OK', "Information reçue"),
    ('NON_TROUVE', "Personne non trouvée"),
    ('INCOMPLET', "Fiche incomplète"),
    ('ERREUR', "Service indisponible"),
]


class SituationExterne(models.Model):
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE,
                                     related_name='situations_externes')
    source = models.CharField(max_length=20, choices=SOURCES)
    statut_appel = models.CharField(max_length=12, choices=STATUTS_APPEL)
    resume = models.CharField(max_length=255, help_text="Phrase affichée à l'agent")
    est_beneficiaire = models.BooleanField(null=True, blank=True)
    donnees = models.JSONField(default=dict, blank=True, help_text="Données utiles uniquement (minimisées)")
    date_maj = models.DateTimeField(help_text="Date de dernière mise à jour de l'information")
    maj_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='+')
    environnement = models.CharField(max_length=15, default='bac_a_sable')

    class Meta:
        unique_together = ('beneficiaire', 'source')
        ordering = ['source']
        verbose_name = "Situation externe (API Particulier)"
        verbose_name_plural = "Situations externes (API Particulier)"

    def __str__(self):
        return f"{self.beneficiaire} – {self.get_source_display()} : {self.resume}"


class JournalAppelAPI(models.Model):
    """Traçabilité : chaque consultation d'un organisme par un agent."""
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE,
                                     related_name='+')
    source = models.CharField(max_length=20, choices=SOURCES)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    related_name='+')
    date = models.DateTimeField(auto_now_add=True)
    code_http = models.PositiveSmallIntegerField(null=True, blank=True)
    statut_appel = models.CharField(max_length=12, choices=STATUTS_APPEL)
    environnement = models.CharField(max_length=15, default='bac_a_sable')

    class Meta:
        ordering = ['-date']
        verbose_name = "Journal des appels API Particulier"
        verbose_name_plural = "Journal des appels API Particulier"


# -----------------------------------------------------------------------------
# Passerelle RDV Service Public (ANCT) — désactivée tant que RDVSP_ACTIF n'est pas à 1
# -----------------------------------------------------------------------------
class CompteRDVSP(models.Model):
    """Connexion d'un agent CID à son compte RDV Service Public (OAuth2, un jeton par agent)."""
    utilisateur = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                       related_name='compte_rdvsp')
    agent_id = models.CharField(max_length=30, blank=True, help_text="Identifiant de l'agent côté RDV Service Public")
    jeton_acces = models.TextField()
    jeton_renouvellement = models.TextField(blank=True)
    expire_le = models.DateTimeField()
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Compte RDV Service Public d'un agent"
        verbose_name_plural = "Comptes RDV Service Public des agents"

    def __str__(self):
        return f"{self.utilisateur} (agent RDV-SP {self.agent_id or '?'})"


class LienUsagerRDVSP(models.Model):
    """Correspondance entre un usager CID et son identifiant usager côté RDV Service Public."""
    beneficiaire = models.OneToOneField('beneficiaire.Beneficiaire', on_delete=models.CASCADE,
                                        related_name='lien_rdvsp')
    usager_rdvsp_id = models.CharField(max_length=30)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lien usager ↔ RDV Service Public"
        verbose_name_plural = "Liens usagers ↔ RDV Service Public"

    def __str__(self):
        return f"{self.beneficiaire} → usager RDV-SP {self.usager_rdvsp_id}"


class AppelRDVSP(models.Model):
    """Traçabilité de chaque appel à RDV Service Public (qui, quand, pour quel usager, résultat)."""
    ACTIONS = [
        ('CONNEXION', "Connexion de l'agent"),
        ('PLAN_RDV', "Préparation d'un rendez-vous"),
        ('LISTE_RDV', "Lecture des rendez-vous"),
        ('STATUT_RDV', "Mise à jour du statut d'un rendez-vous"),
    ]
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                    related_name='+')
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE, null=True,
                                     blank=True, related_name='+')
    action = models.CharField(max_length=12, choices=ACTIONS)
    code_http = models.PositiveSmallIntegerField(null=True, blank=True)
    reussi = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "Journal des appels RDV Service Public"
        verbose_name_plural = "Journal des appels RDV Service Public"
