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
from django.utils import timezone


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
    fiche_avec_nir = models.BooleanField(
        "La fiche de liaison demande le n° de sécurité sociale", default=False,
        help_text="Le n° de sécurité sociale n'est imprimé sur la fiche de liaison que pour les actions qui l'exigent.")
    validation_pole = models.BooleanField(
        "Prescription validée par le pôle insertion", default=False,
        help_text="Les prescriptions vers cette action passent par le pôle avant d'être adressées au porteur.")
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


# =============================================================================
# Étape 2 : le contrat et son circuit
# =============================================================================

class ParametresRSA(models.Model):
    """Règles du contrat, réglables en administration (une seule ligne : ParametresRSA.courant())."""
    nom_contrat = models.CharField("Nom du contrat", max_length=120, default="Contrat d'engagement",
                                   help_text="Nom affiché dans CID et sur le contrat imprimé.")
    duree_defaut_mois = models.PositiveSmallIntegerField("Durée proposée par défaut (mois)", default=6)
    duree_max_mois = models.PositiveSmallIntegerField("Durée maximale d'un contrat (mois)", default=12)
    duree_sauf_action_mois = models.PositiveSmallIntegerField(
        "Durée d'un contrat « validé sauf action » (mois)", default=3,
        help_text="Le contrat est validé pour cette durée ; l'action non retenue est retravaillée d'ici là.")
    delai_alerte_jours = models.PositiveSmallIntegerField(
        "Alerte de renouvellement (jours avant la fin)", default=30,
        help_text="Le bénéficiaire s'engage à renouveler son contrat un mois avant son échéance.")
    heures_hebdo_min = models.PositiveSmallIntegerField(
        "Activité hebdomadaire minimale (heures)", default=15,
        help_text="Contrat d'engagement sur mesure : au moins 15 heures d'activité par semaine.")
    age_limite_certificat = models.PositiveSmallIntegerField(
        "Âge en dessous duquel un contrat santé exige un certificat médical", default=60)

    class Meta:
        verbose_name = "Paramètres du contrat RSA"
        verbose_name_plural = "Paramètres du contrat RSA"

    def __str__(self):
        return "Paramètres du contrat RSA"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def courant(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


def ajouter_mois(d, mois):
    from dateutil.relativedelta import relativedelta
    return d + relativedelta(months=mois)


class ContratInsertion(models.Model):
    # ---------------------------------------------------------------- types et statuts
    OUVERTURE, PROLONGEMENT, RETABLISSEMENT = 'OUVERTURE', 'PROLONGEMENT', 'RETABLISSEMENT'
    TYPES = [(OUVERTURE, "Ouverture"), (PROLONGEMENT, "Prolongement"),
             (RETABLISSEMENT, "Rétablissement (après une suspension)")]
    NATURES = [('SOCIAL', "Social"), ('EMPLOI', "Emploi"), ('SANTE', "Santé"), ('LOGEMENT', "Logement")]

    BROUILLON, TRANSMIS, RECU = 'BROUILLON', 'TRANSMIS', 'RECU'
    VALIDE, VALIDE_SAUF_ACTION, AJOURNE, NON_VALIDE, ANNULE = (
        'VALIDE', 'VALIDE_SAUF_ACTION', 'AJOURNE', 'NON_VALIDE', 'ANNULE')
    STATUTS = [(BROUILLON, "En préparation"), (TRANSMIS, "Transmis au pôle"),
               (RECU, "Reçu au pôle, en attente de commission"), (VALIDE, "Validé"),
               (VALIDE_SAUF_ACTION, "Validé sauf action"), (AJOURNE, "Ajourné (à reprendre)"),
               (NON_VALIDE, "Non validé"), (ANNULE, "Annulé")]
    MODIFIABLES = (BROUILLON, AJOURNE)
    DECIDES = (VALIDE, VALIDE_SAUF_ACTION, NON_VALIDE)
    DECISIONS = [(VALIDE, "Validé"), (VALIDE_SAUF_ACTION, "Validé sauf action"),
                 (AJOURNE, "Ajourné (retour au référent)"), (NON_VALIDE, "Non validé")]

    NIVEAUX_ETUDES = [('', "—"), ('SANS', "Sans diplôme"), ('N3', "CAP, BEP (niveau 3)"), ('N4', "Bac (niveau 4)"),
                      ('N5', "Bac + 2 (niveau 5)"), ('N6', "Licence, bac + 3 (niveau 6)"),
                      ('N7', "Master et plus (niveau 7 ou 8)"), ('ETR', "Diplôme étranger")]
    LOGEMENTS = [('', "—"), ('LOCATAIRE', "Locataire"), ('PROPRIETAIRE', "Propriétaire"),
                 ('HEBERGE', "Hébergé(e) chez un tiers"), ('STRUCTURE', "Hébergé(e) en structure"),
                 ('SANS', "Sans logement"), ('AUTRE', "Autre")]
    MODES_CERTIFICAT = [('', "—"), ('PLI', "Sous pli cacheté, adressé au médecin du pôle"),
                        ('MSSANTE', "Par messagerie sécurisée de santé (MSSanté)")]
    AVIS = [('FAVORABLE', "Favorable"), ('DEFAVORABLE', "Défavorable")]
    DECISIONS_TRANSPORT = [('', "—"), ('OUI', "Accordée"), ('NON', "Refusée")]
    MOTIFS_TRANSPORT = [('', "—"), ('DEROGATION', "Par dérogation"),
                        ('DUREE_MAX', "Durée maximale déjà accordée"), ('CONDITIONS', "Conditions non remplies")]

    # ---------------------------------------------------------------- dossier
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE,
                                     related_name='contrats_insertion', verbose_name="Bénéficiaire")
    mds = models.ForeignKey('mds.MDS', on_delete=models.SET_NULL, null=True, related_name='contrats_insertion',
                            verbose_name="MDS")
    pole = models.ForeignKey(PoleInsertion, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='contrats', verbose_name="Pôle insertion")
    referent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name='contrats_insertion', verbose_name="Référent")
    precedent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='suivants',
                                  verbose_name="Contrat précédent")
    type_contrat = models.CharField("Type", max_length=15, choices=TYPES, default=OUVERTURE)
    nature = models.CharField("Nature du contrat", max_length=10, choices=NATURES, default='SOCIAL')
    statut = models.CharField("Statut", max_length=20, choices=STATUTS, default=BROUILLON)

    # ---------------------------------------------------------------- conjoint
    conjoint = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='+', verbose_name="Conjoint")
    conjoint_situation = models.CharField("Situation du conjoint", max_length=200, blank=True)
    conjoint_operateur = models.CharField("Opérateur du conjoint", max_length=200, blank=True)
    conjoint_referent = models.CharField("Référent du conjoint", max_length=200, blank=True)

    # ---------------------------------------------------------------- diagnostic
    inscrit_france_travail = models.BooleanField("Inscrit(e) à France Travail", default=False)
    identifiant_france_travail = models.CharField("Identifiant France Travail", max_length=20, blank=True)
    niveau_etudes = models.CharField("Niveau d'études", max_length=5, choices=NIVEAUX_ETUDES, blank=True)
    formation = models.CharField("Formation", max_length=255, blank=True)
    experience = models.TextField("Expérience professionnelle", blank=True)
    dernier_emploi = models.CharField("Dernier emploi", max_length=200, blank=True)
    dernier_emploi_annee = models.PositiveSmallIntegerField("Année du dernier emploi", null=True, blank=True)
    dernier_emploi_duree = models.CharField("Durée du dernier emploi", max_length=50, blank=True)
    emploi_recherche = models.CharField("Emploi recherché", max_length=200, blank=True)
    francais_parle = models.BooleanField("Parle le français", default=True)
    francais_lu = models.BooleanField("Lit le français", default=True)
    francais_ecrit = models.BooleanField("Écrit le français", default=True)
    permis_b = models.BooleanField("Permis B", default=False)
    autres_permis = models.CharField("Autres permis", max_length=100, blank=True)
    vehicule = models.BooleanField("Véhiculé(e)", default=False)
    couverture_base = models.CharField("Couverture maladie de base", max_length=100, blank=True)
    couverture_complementaire = models.CharField("Complémentaire santé", max_length=100, blank=True)
    logement = models.CharField("Logement", max_length=15, choices=LOGEMENTS, blank=True)
    logement_precision = models.CharField("Précision sur le logement", max_length=200, blank=True)

    # ---------------------------------------------------------------- incidence financière
    incidence_creation_activite = models.BooleanField("Création d'activité", default=False)
    incidence_formation = models.BooleanField("Formation", default=False)
    incidence_frais_annexes = models.BooleanField("Frais annexes", default=False)

    # ---------------------------------------------------------------- parole et engagements
    parole_situation = models.TextField("Ma situation actuelle", blank=True)
    parole_deja_fait = models.TextField("Ce que j'ai déjà fait", blank=True)
    parole_souhaits = models.TextField("Ce que je souhaite faire", blank=True)
    objectifs = models.TextField("Objectifs", blank=True)
    etapes = models.TextField("Étapes", blank=True)
    observations = models.TextField("Observations du référent", blank=True)
    heures_activite_hebdo = models.PositiveSmallIntegerField("Heures d'activité par semaine", default=15)
    duree_proposee_mois = models.PositiveSmallIntegerField("Durée proposée (mois)", default=6)
    aide_transport_urbain = models.BooleanField("Aide aux transports : urbain", default=False)
    aide_transport_interurbain = models.BooleanField("Aide aux transports : interurbain", default=False)
    engagement_renouvellement = models.BooleanField(
        "Le bénéficiaire s'engage à renouveler son contrat un mois avant son échéance", default=False)
    accord_allocataire = models.BooleanField("Accord du bénéficiaire sur le contenu du contrat", default=False)

    # ---------------------------------------------------------------- circuit
    date_etablissement = models.DateField("Établi le", null=True, blank=True)
    date_signature = models.DateField("Signé le", null=True, blank=True)
    date_transmission = models.DateField("Transmis au pôle le", null=True, blank=True)
    date_reception = models.DateField("Reçu au pôle le", null=True, blank=True)
    recu_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='+', verbose_name="Reçu par")

    # ---------------------------------------------------------------- contrat santé (aucun contenu médical)
    certificat_mode = models.CharField("Transmission du certificat médical", max_length=10,
                                       choices=MODES_CERTIFICAT, blank=True)
    certificat_demande_le = models.DateField("Certificat demandé au médecin traitant le", null=True, blank=True)
    certificat_recu_le = models.DateField("Certificat reçu par le médecin du pôle le", null=True, blank=True)
    avis_medical = models.CharField("Avis du médecin du pôle", max_length=12, choices=AVIS, blank=True)
    avis_motivation = models.TextField("Motivation de l'avis", blank=True,
                                       help_text="Sans aucun détail médical : le certificat reste chez le médecin.")
    avis_le = models.DateField("Avis donné le", null=True, blank=True)
    avis_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='+', verbose_name="Médecin")

    # ---------------------------------------------------------------- commission de validation
    decision = models.CharField("Décision", max_length=20, choices=DECISIONS, blank=True)
    date_decision = models.DateField("Décision du", null=True, blank=True)
    duree_validee_mois = models.PositiveSmallIntegerField("Durée validée (mois)", null=True, blank=True)
    date_debut = models.DateField("Du", null=True, blank=True)
    date_fin = models.DateField("Au", null=True, blank=True)
    motif_decision = models.TextField("Motif (ajournement, non-validation)", blank=True)
    decision_transport = models.CharField("Aide aux transports", max_length=3, choices=DECISIONS_TRANSPORT, blank=True)
    motif_transport = models.CharField("Motif (aide aux transports)", max_length=12, choices=MOTIFS_TRANSPORT,
                                       blank=True)
    commentaire_commission = models.TextField("Commentaires de la commission", blank=True)
    decide_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='+', verbose_name="Cadre")

    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Contrat d'insertion"
        verbose_name_plural = "Contrats d'insertion"
        ordering = ['-date_etablissement', '-pk']

    def __str__(self):
        return f"{self.numero} – {self.beneficiaire}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('insertion:contrat_detail', args=[self.pk])

    @property
    def numero(self):
        annee = (self.date_etablissement or timezone.localdate()).year
        return f"C{annee}-{self.pk or 0:05d}"

    # ---------------------------------------------------------------- règles
    @property
    def modifiable(self):
        return self.statut in self.MODIFIABLES

    def age_beneficiaire(self, le=None):
        from dateutil.relativedelta import relativedelta
        n = self.beneficiaire.date_naissance
        return relativedelta(le or self.date_etablissement or timezone.localdate(), n).years if n else None

    @property
    def certificat_obligatoire(self):
        """Contrat santé d'une personne de moins de 60 ans (paramétrable) : certificat du médecin traitant."""
        age = self.age_beneficiaire()
        return self.nature == 'SANTE' and age is not None and age < ParametresRSA.courant().age_limite_certificat

    @property
    def en_vigueur(self):
        aujourd_hui = timezone.localdate()
        return (self.statut in (self.VALIDE, self.VALIDE_SAUF_ACTION) and self.date_debut and self.date_fin
                and self.date_debut <= aujourd_hui <= self.date_fin)

    @property
    def jours_restants(self):
        if self.statut in (self.VALIDE, self.VALIDE_SAUF_ACTION) and self.date_fin:
            return (self.date_fin - timezone.localdate()).days
        return None

    @property
    def alerte(self):
        """« expire » (échéance passée), « renouveler » (dans le délai d'alerte) ou None."""
        j = self.jours_restants
        if j is None or self.suivants.exclude(statut__in=(self.ANNULE, self.NON_VALIDE)).exists():
            return None
        if j < 0:
            return "expire"
        if j <= ParametresRSA.courant().delai_alerte_jours:
            return "renouveler"
        return None

    def date_fin_pour(self, debut, mois):
        from datetime import timedelta
        return ajouter_mois(debut, mois) - timedelta(days=1)

    def manques_transmission(self):
        """Ce qui empêche de transmettre le contrat au pôle (liste de phrases, vide si tout va bien)."""
        manques = []
        if not self.date_signature:
            manques.append("la date de signature")
        if not self.accord_allocataire:
            manques.append("l'accord du bénéficiaire")
        if not self.objectifs.strip():
            manques.append("les objectifs")
        if not self.lignes.exists():
            manques.append("au moins une action")
        if self.certificat_obligatoire and not self.certificat_mode:
            manques.append("la transmission du certificat médical (contrat santé)")
        if not self.pole_id:
            manques.append("un pôle insertion couvrant la MDS (à rattacher en administration)")
        return manques

    @property
    def attend_avis_medical(self):
        return self.certificat_obligatoire and not self.avis_medical


class LigneActionContrat(models.Model):
    contrat = models.ForeignKey(ContratInsertion, on_delete=models.CASCADE, related_name='lignes')
    action = models.ForeignKey(ActionInsertion, on_delete=models.PROTECT, null=True, blank=True, related_name='lignes_contrat',
                               verbose_name="Action du référentiel")
    libelle = models.CharField("Autre démarche", max_length=200, blank=True,
                               help_text="Si la démarche n'est pas une action du référentiel.")
    date_entree = models.DateField("Entrée", null=True, blank=True)
    date_sortie = models.DateField("Sortie", null=True, blank=True)
    motif_sortie = models.CharField("Motif de sortie", max_length=200, blank=True)
    prescription = models.ForeignKey('PrescriptionInsertion', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='lignes_contrat', verbose_name="Prescription",
                                     help_text="Ligne tenue à jour par la prescription (entrée, sortie, motif).")
    non_retenue = models.BooleanField("Non retenue par la commission", default=False)
    motif_non_retenue = models.CharField("Motif (action non retenue)", max_length=255, blank=True)

    class Meta:
        verbose_name = "Action du contrat"
        verbose_name_plural = "Actions du contrat"
        ordering = ['pk']

    def __str__(self):
        return self.intitule

    @property
    def intitule(self):
        return self.action.libelle if self.action_id else (self.libelle or "—")

    def clean(self):
        if not self.action_id and not self.libelle.strip():
            raise ValidationError("Choisissez une action du référentiel ou décrivez la démarche.")


class HistoriqueContrat(models.Model):
    """Journal du circuit : qui a fait quoi, et quand (création, transmission, réception, avis, décision…)."""
    contrat = models.ForeignKey(ContratInsertion, on_delete=models.CASCADE, related_name='historique')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    action = models.CharField(max_length=200)
    commentaire = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-pk']
        verbose_name = "Historique d'un contrat"
        verbose_name_plural = "Historique des contrats"


# =============================================================================
# Étape 3 : les prescriptions
# =============================================================================

class QuestionAction(models.Model):
    """Question propre à une action, posée dans la prescription (permis de conduire, garde d'enfants…)."""
    TEXTE, OUI_NON, CHOIX, CHOIX_MULTIPLE, DATE, NOMBRE = 'TEXTE', 'OUI_NON', 'CHOIX', 'CHOIX_MULTIPLE', 'DATE', 'NOMBRE'
    TYPES = [(TEXTE, "Texte"), (OUI_NON, "Oui / non"), (CHOIX, "Un choix dans une liste"),
             (CHOIX_MULTIPLE, "Plusieurs choix dans une liste"), (DATE, "Date"), (NOMBRE, "Nombre")]
    action = models.ForeignKey(ActionInsertion, on_delete=models.CASCADE, related_name='questions')
    libelle = models.CharField("Question", max_length=255)
    type_reponse = models.CharField("Type de réponse", max_length=15, choices=TYPES, default=TEXTE)
    choix = models.TextField("Choix proposés", blank=True, help_text="Un choix par ligne (listes seulement).")
    aide = models.CharField("Aide", max_length=255, blank=True)
    obligatoire = models.BooleanField("Obligatoire", default=False)
    restreinte = models.BooleanField(
        "Réponse à accès restreint", default=False,
        help_text="Visible seulement des agents de la MDS du bénéficiaire, et du cadre et du médecin du pôle "
                  "(ex. grille d'aide à la décision santé). Jamais de détail médical.")
    ordre = models.PositiveSmallIntegerField("Ordre", default=0)

    class Meta:
        ordering = ['ordre', 'pk']
        verbose_name = "Question propre à l'action"
        verbose_name_plural = "Questions propres à l'action"

    def __str__(self):
        return self.libelle

    @property
    def liste_choix(self):
        return [c.strip() for c in self.choix.splitlines() if c.strip()]


FREINS = [
    ('MOBILITE', "Mobilité"), ('GARDE', "Garde d'enfants"), ('LANGUE', "Langue, savoirs de base"),
    ('LOGEMENT', "Logement"), ('FAMILLE', "Situation familiale"), ('SANTE', "Santé"), ('FINANCES', "Finances, budget"),
    ('ADMINISTRATIF', "Démarches administratives, numérique"), ('ISOLEMENT', "Isolement"),
    ('PROJET', "Projet professionnel"), ('RECHERCHE_EMPLOI', "Techniques de recherche d'emploi"),
]


class PrescriptionInsertion(models.Model):
    BROUILLON, A_VALIDER, REFUSEE, EN_ATTENTE = 'BROUILLON', 'A_VALIDER', 'REFUSEE', 'EN_ATTENTE'
    INTEGREE, NON_INTEGREE, TERMINEE, ARRETEE, REORIENTEE, ANNULEE = (
        'INTEGREE', 'NON_INTEGREE', 'TERMINEE', 'ARRETEE', 'REORIENTEE', 'ANNULEE')
    STATUTS = [(BROUILLON, "En préparation"), (A_VALIDER, "À valider par le pôle"), (REFUSEE, "Refusée par le pôle"),
               (EN_ATTENTE, "Adressée au porteur, en attente d'intégration"), (INTEGREE, "Intégrée, en cours"),
               (NON_INTEGREE, "Non intégrée"), (TERMINEE, "Terminée"), (ARRETEE, "Arrêtée"),
               (REORIENTEE, "Réorientée"), (ANNULEE, "Annulée")]
    MODIFIABLES = (BROUILLON,)
    OUVERTES = (A_VALIDER, EN_ATTENTE, INTEGREE)
    SORTIES = [(TERMINEE, "Terminée (parcours mené à son terme)"), (ARRETEE, "Arrêtée"),
               (REORIENTEE, "Réorientée")]

    SITUATIONS_RSA = [('', "—"), ('SOCLE', "RSA socle"), ('MAJORE', "RSA majoré")]
    DEMANDE_PAR = [('PERSONNE', "Demandée par la personne"), ('TS', "Proposée par le travailleur social")]
    ISSUES_RDV = [('', "—"), ('PRESENT', "Présent(e)"), ('ABSENT', "Absent(e)"), ('EXCUSE', "Excusé(e)"),
                  ('RECONVOQUE', "Reconvoqué(e)")]
    REORIENTATIONS = [('', "—"), ('ASI', "Accompagnement social individuel (ASI)"),
                      ('DISPOSITIF', "Autre dispositif"), ('FRANCE_TRAVAIL', "France Travail")]

    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE,
                                     related_name='prescriptions_insertion', verbose_name="Bénéficiaire")
    mds = models.ForeignKey('mds.MDS', on_delete=models.SET_NULL, null=True, related_name='prescriptions_insertion')
    pole = models.ForeignKey(PoleInsertion, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='prescriptions', verbose_name="Pôle insertion")
    prescripteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                     related_name='prescriptions_insertion', verbose_name="Prescripteur")
    action = models.ForeignKey(ActionInsertion, on_delete=models.PROTECT, related_name='prescriptions',
                               verbose_name="Action")
    contrat = models.ForeignKey(ContratInsertion, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='prescriptions', verbose_name="Contrat")
    statut = models.CharField("Statut", max_length=15, choices=STATUTS, default=BROUILLON)
    date_prescription = models.DateField("Date de la prescription", null=True, blank=True)

    # ---------------------------------------------------------------- tronc commun (prérempli, modifiable)
    situation_rsa = models.CharField("Situation RSA", max_length=10, choices=SITUATIONS_RSA, blank=True)
    qpv = models.BooleanField("Habite un quartier prioritaire (QPV)", default=False)
    rqth = models.BooleanField("Reconnaissance de la qualité de travailleur handicapé (RQTH)", default=False)
    inscrit_france_travail = models.BooleanField("Inscrit(e) à France Travail", default=False)
    identifiant_france_travail = models.CharField("Identifiant France Travail", max_length=20, blank=True)
    qualification = models.CharField("Qualification, niveau", max_length=200, blank=True)
    inactivite = models.CharField("Sans activité depuis", max_length=100, blank=True)
    freins = models.JSONField("Freins", default=list, blank=True)
    diagnostic = models.TextField("Diagnostic", blank=True)
    avis_motive = models.TextField("Avis motivé du prescripteur", blank=True)
    objectifs = models.TextField("Objectifs de l'orientation", blank=True)
    demande_par = models.CharField("Orientation", max_length=10, choices=DEMANDE_PAR, default='TS')
    pieces_fournies = models.JSONField("Pièces fournies", default=list, blank=True)
    consentement = models.BooleanField(
        "Le bénéficiaire accepte que ces informations soient transmises au porteur de l'action", default=False)
    date_signature = models.DateField("Signée le", null=True, blank=True)

    # ---------------------------------------------------------------- pôle
    date_envoi = models.DateField("Adressée le", null=True, blank=True)
    valide_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='+', verbose_name="Validée par")
    date_validation = models.DateField("Validée ou refusée le", null=True, blank=True)
    motif_refus = models.TextField("Motif du refus", blank=True)

    # ---------------------------------------------------------------- retour du porteur
    premier_rdv_le = models.DateField("Premier rendez-vous le", null=True, blank=True)
    premier_rdv_issue = models.CharField("Premier rendez-vous", max_length=12, choices=ISSUES_RDV, blank=True)
    diagnostic_finalise = models.BooleanField("Diagnostic finalisé par le porteur", default=False)
    date_entree = models.DateField("Entrée dans l'action le", null=True, blank=True)
    motif_non_integration = models.CharField("Motif de non-intégration", max_length=255, blank=True)
    date_sortie = models.DateField("Sortie le", null=True, blank=True)
    motif_sortie = models.CharField("Motif de sortie", max_length=255, blank=True)
    reorientation = models.CharField("Réorientation vers", max_length=15, choices=REORIENTATIONS, blank=True)
    reorientation_precision = models.CharField("Précision sur la réorientation", max_length=255, blank=True)
    commentaire_porteur = models.TextField("Commentaire du porteur", blank=True)

    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_prescription', '-pk']
        verbose_name = "Prescription"
        verbose_name_plural = "Prescriptions"

    def __str__(self):
        return f"{self.numero} – {self.action.libelle}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('insertion:prescription_detail', args=[self.pk])

    @property
    def numero(self):
        annee = (self.date_prescription or timezone.localdate()).year
        return f"P{annee}-{self.pk or 0:05d}"

    @property
    def modifiable(self):
        return self.statut in self.MODIFIABLES

    @property
    def libelles_freins(self):
        noms = dict(FREINS)
        return [noms.get(f, f) for f in self.freins]

    def manques_envoi(self):
        manques = []
        if not self.consentement:
            manques.append("le consentement du bénéficiaire")
        if not self.objectifs.strip():
            manques.append("les objectifs de l'orientation")
        for q in self.action.questions.filter(obligatoire=True):
            r = self.reponses.filter(question=q).first()
            if not r or not r.valeur.strip():
                manques.append(f"la réponse à « {q.libelle} »")
        return manques


class ReponseQuestion(models.Model):
    prescription = models.ForeignKey(PrescriptionInsertion, on_delete=models.CASCADE, related_name='reponses')
    question = models.ForeignKey(QuestionAction, on_delete=models.CASCADE, related_name='reponses')
    valeur = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['prescription', 'question'], name='reponse_unique')]


class HistoriquePrescription(models.Model):
    prescription = models.ForeignKey(PrescriptionInsertion, on_delete=models.CASCADE, related_name='historique')
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    action = models.CharField(max_length=200)
    commentaire = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-pk']
