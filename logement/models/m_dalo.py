# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/models/m_dalo.py
from django.conf import settings
from django.db import models


class RecoursDALO(models.Model):
    """Données du recours amiable DALO (Cerfa 15036*02), un par usager (un seul requérant par foyer).
    Préremplies depuis la fiche usager et la demande de logement social, puis corrigées par l'AS."""
    SITUATIONS = [
        ('DEPOURVU', "8.1 Dépourvu(e) de logement"),
        ('HEBERGE', "8.2 Hébergé(e) chez un particulier"),
        ('EXPULSION', "8.3 Menacé(e) d'expulsion sans relogement"),
        ('STRUCTURE', "8.4 Hébergé(e) de façon continue dans une structure"),
        ('TRANSITION', "8.5 Logé(e) temporairement (logement de transition, logement-foyer…)"),
        ('INSALUBRE', "8.6 Logé(e) dans un logement insalubre ou dangereux"),
        ('NON_DECENT', "8.7 Logement non décent"),
        ('SUROCCUPE', "8.8 Logement manifestement sur-occupé"),
        ('DELAI', "8.9 Délai anormalement long de la demande de logement social"),
    ]
    NATIONALITES = [('FR', "Française"), ('UE', "Union européenne"), ('HORS_UE', "Hors Union européenne")]
    LOGEMENTS = [('PROPRIETAIRE', "Propriétaire occupant"), ('SOCIAL', "Locataire d'un logement social"),
                 ('PRIVE', "Locataire ou sous-locataire d'un logement privé"), ('AUTRE', "Autre")]

    beneficiaire = models.OneToOneField('beneficiaire.Beneficiaire', on_delete=models.CASCADE,
                                        related_name='recours_dalo')
    civilite = models.CharField(max_length=5, blank=True, choices=[('M', "Monsieur"), ('MME', "Madame")])
    nom_naissance = models.CharField(max_length=60, blank=True)
    nom_usage = models.CharField(max_length=60, blank=True)
    prenoms = models.CharField(max_length=120, blank=True)
    date_naissance = models.CharField(max_length=10, blank=True, help_text="JJ/MM/AAAA")
    nationalite = models.CharField(max_length=8, blank=True, choices=NATIONALITES)
    nud = models.CharField("Numéro unique d'enregistrement", max_length=30, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    telephone_portable = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=120, blank=True)
    adresse_numero = models.CharField(max_length=10, blank=True)
    adresse_voie = models.CharField(max_length=150, blank=True)
    adresse_complement = models.CharField(max_length=150, blank=True)
    code_postal = models.CharField(max_length=5, blank=True)
    commune = models.CharField(max_length=100, blank=True)
    logement = models.CharField(max_length=12, blank=True, choices=LOGEMENTS)
    logement_autre = models.CharField(max_length=150, blank=True)
    bailleur = models.CharField("Nom du bailleur figurant sur la quittance", max_length=150, blank=True)
    numero_allocataire = models.CharField(max_length=20, blank=True)
    personnes = models.TextField("Personnes à loger en plus de vous-même", blank=True,
                                 help_text="Une par ligne : Nom;Prénom;JJ/MM/AAAA;Lien de parenté")
    situations = models.JSONField(default=list, blank=True, help_text="Codes des situations cochées (8.1 à 8.9)")
    nature_local = models.CharField("8.1 Nature du local", max_length=120, blank=True)
    hebergeurs = models.TextField("8.2 Personnes qui vous hébergent (nom, adresse, depuis quand)", blank=True)
    hebergement_nb_personnes = models.CharField("8.2 Nombre de personnes dans le logement", max_length=10, blank=True)
    hebergement_surface = models.CharField("8.2 Surface (m²)", max_length=10, blank=True)
    hebergement_pieces = models.CharField("8.2 Nombre de pièces", max_length=10, blank=True)
    structure_nom = models.CharField("8.4 Nom de la structure", max_length=150, blank=True)
    structure_date = models.CharField("8.4 Date d'entrée dans la structure", max_length=10, blank=True)
    surface_totale = models.CharField("8.8 Surface totale (m²)", max_length=10, blank=True)
    nombre_pieces = models.CharField("8.8 Nombre de pièces", max_length=10, blank=True)
    assistant_nom = models.CharField("10.1.1 Nom de la personne qui vous assiste", max_length=120, blank=True)
    assistant_organisme = models.CharField("10.1.1 Nom de son organisme", max_length=150, blank=True)
    assistant_adresse_numero = models.CharField(max_length=10, blank=True)
    assistant_adresse_voie = models.CharField(max_length=150, blank=True)
    assistant_code_postal = models.CharField(max_length=5, blank=True)
    assistant_commune = models.CharField(max_length=100, blank=True)
    assistant_telephone = models.CharField(max_length=20, blank=True)
    argumentaire = models.TextField("11. Argumentaire libre", blank=True)
    date_modification = models.DateTimeField(auto_now=True)
    modifie_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='recours_dalo_modifies')

    class Meta:
        verbose_name = "Recours DALO (Cerfa 15036)"
        verbose_name_plural = "Recours DALO (Cerfa 15036)"

    def __str__(self):
        return f"Recours DALO – {self.beneficiaire}"
