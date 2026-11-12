# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/models.py
"""Suivi du traitement des relations avec les usagers (RU)."""
import calendar
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.mixins import AuditedMixin, TimestampedMixin


class DemandeRelationUsager(AuditedMixin):
    """Une saisine reçue par le SAS ou directement par une MDS."""

    class Canal(models.TextChoices):
        COURRIER = "COURRIER", "Courrier"
        CONTACT = "CONTACT", "Contact physique"
        COURRIEL = "COURRIEL", "Courriel"
        PLATEFORME_13 = "PLATEFORME_13", "Plateforme 13 à votre écoute"
        AUTRE = "AUTRE", "Autre"

    class Priorite(models.TextChoices):
        ORDINAIRE = "ORDINAIRE", "Courrier ordinaire"
        SIGNALEE = "SIGNALEE", "Courrier signalé / urgent"

    class Circuit(models.TextChoices):
        SAS = "SAS", "Réponse directe ou réorientation par le SAS"
        MDS = "MDS", "Évaluation par une MDS"

    class Statut(models.TextChoices):
        A_TRAITER_SAS = "A_TRAITER_SAS", "À traiter / transmettre par le SAS"
        A_TRAITER_MDS = "A_TRAITER_MDS", "À affecter par la MDS"
        EN_EVALUATION = "EN_EVALUATION", "Évaluation en cours"
        A_VALIDER_CADRE = "A_VALIDER_CADRE", "À valider par le cadre MDS"
        A_VALIDER_SAS = "A_VALIDER_SAS", "À finaliser par le SAS"
        CLOTUREE = "CLOTUREE", "Clôturée"

    canal = models.CharField("Canal de réception", max_length=20, choices=Canal.choices)
    priorite = models.CharField("Priorité", max_length=12, choices=Priorite.choices, default=Priorite.ORDINAIRE)
    circuit = models.CharField("Transmission", max_length=8, choices=Circuit.choices)
    statut = models.CharField("État", max_length=20, choices=Statut.choices, default=Statut.A_TRAITER_SAS, db_index=True)
    date_reception = models.DateField("Date de réception", default=timezone.localdate, db_index=True)
    date_notification_mds = models.DateField(
        "Date d'envoi à la MDS", null=True, blank=True, db_index=True,
        help_text="Déclenche le délai de réponse. Est renseignée au moment de l'envoi SAS → MDS.",
    )
    date_cloture_souhaitee = models.DateField("À clôturer avant le", null=True, blank=True)
    mds = models.ForeignKey(
        "mds.MDS", on_delete=models.PROTECT, null=True, blank=True,
        related_name="demandes_relation_usager", verbose_name="Maison départementale de la solidarité choisie",
    )
    reference_sap = models.CharField("N° SAP", max_length=80, blank=True)
    emetteur = models.CharField("Service / organisme émetteur", max_length=200, blank=True)
    reference_externe = models.CharField("Référence externe", max_length=100, blank=True)
    nom_usager = models.CharField("Nom de l'usager", max_length=150)
    prenom_usager = models.CharField("Prénom de l'usager", max_length=150, blank=True)
    adresse_usager = models.TextField("Adresse de l'usager", blank=True)
    coordonnees_usager = models.CharField("Téléphone / courriel utile", max_length=250, blank=True)
    objet = models.CharField("Motif de la demande", max_length=250)
    resume_demande = models.TextField("Demande de l'usager", help_text="Saisir uniquement les éléments nécessaires au traitement.")
    situation_familiale = models.CharField("Situation familiale", max_length=150, blank=True)
    nombre_enfants = models.PositiveSmallIntegerField("Nombre d'enfants à charge", null=True, blank=True)
    revenu_principal = models.CharField("Revenu principal", max_length=150, blank=True)
    age_usager = models.PositiveSmallIntegerField("Âge du demandeur", null=True, blank=True)
    usager_informe_transmission = models.BooleanField(
        "Usager informé des éléments transmis", default=False,
        help_text="Tracer l'information de l'usager lorsque des éléments sur sa situation sont transmis.",
    )
    date_information_usager = models.DateField("Date d'information de l'usager", null=True, blank=True)
    accompagnement_autre_service = models.BooleanField("Usager accompagné par un autre service", default=False)
    usager_informe_liaison = models.BooleanField("Usager informé de la liaison avec l'autre service", default=False)

    agent_assigne = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="demandes_ru_assignees", verbose_name="Nom du travailleur social chargé de l'évaluation",
    )
    elements_declaratifs = models.TextField("Éléments déclaratifs de l'usager", blank=True)
    evaluation_sociale = models.TextField("Évaluation sociale synthétique", blank=True)
    modalites_contact = models.TextField("Contacts et démarches réalisés", blank=True)
    situation_actualisee = models.TextField("Situation actualisée", blank=True)
    date_premier_rendez_vous = models.DateField("Date du 1er rendez-vous", null=True, blank=True)
    heure_premier_rendez_vous = models.TimeField("Heure du 1er rendez-vous", null=True, blank=True)
    absence_premier_rendez_vous = models.BooleanField("Ne s'est pas présentée au 1er rendez-vous", default=False)
    courrier_premier_rdv_genere_le = models.DateTimeField("Courrier de 1er rendez-vous généré le", null=True, blank=True)
    date_second_rendez_vous = models.DateField("Date du 2e rendez-vous", null=True, blank=True)
    heure_second_rendez_vous = models.TimeField("Heure du 2e rendez-vous", null=True, blank=True)
    absence_second_rendez_vous = models.BooleanField("Ne s'est pas présentée au 2e rendez-vous", default=False)
    courrier_second_rdv_genere_le = models.DateTimeField("Courrier de 2e rendez-vous généré le", null=True, blank=True)
    problematique_plan = models.TextField(
        "Problématique repérée / plan préconisé", blank=True,
        help_text="Préciser les dates de rendez-vous et communiquer les éléments en lien avec la demande de l'usager.",
    )
    plan_aide = models.TextField("Plan d'aide / actions et échéances", blank=True)
    propositions_reorientation = models.TextField("Propositions de réorientation", blank=True)
    aide_financiere_type = models.CharField("Dispositif d'aide (AMASE, SAA ou autre)", max_length=100, blank=True)
    aide_financiere_proposee = models.BooleanField("Aide financière proposée", default=False)
    decision_aide_financiere = models.CharField("Décision relative à l'aide", max_length=250, blank=True)
    date_aide_financiere = models.DateField("Date de l'aide", null=True, blank=True)
    montant_aide_financiere = models.DecimalField("Montant de l'aide (€)", max_digits=10, decimal_places=2, null=True, blank=True)
    motif_rejet_aide = models.TextField("Motif du rejet de l'aide", blank=True)

    date_soumission_mds = models.DateTimeField("Évaluation transmise au cadre", null=True, blank=True)
    validee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="demandes_ru_validees", verbose_name="Visa du cadre MDS ayant validé",
    )
    initiales_signature_cadre = models.CharField("Initiales de signature du cadre", max_length=8, blank=True)
    date_validation_mds = models.DateTimeField("Date et heure de validation du cadre MDS", null=True, blank=True)
    date_reponse_transmise = models.DateTimeField("Date de transmission de la réponse", null=True, blank=True)
    reponse_transmise_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="demandes_ru_transmises", verbose_name="Agent SAS ayant transmis la réponse",
    )
    date_escalade_direction = models.DateTimeField("Date de transmission à la direction après trois relances", null=True, blank=True)

    class Meta:
        verbose_name = "Demande de relation usager"
        verbose_name_plural = "Demandes de relation usager"
        ordering = ["-date_reception", "-pk"]
        indexes = [
            models.Index(fields=["statut", "date_notification_mds"], name="ru_statut_echeance_idx"),
            models.Index(fields=["mds", "statut"], name="ru_mds_statut_idx"),
        ]

    def clean(self):
        errors = {}
        statuts_apres_envoi_mds = {
            self.Statut.A_TRAITER_MDS, self.Statut.EN_EVALUATION,
            self.Statut.A_VALIDER_CADRE, self.Statut.A_VALIDER_SAS,
        }
        if self.circuit == self.Circuit.MDS and not self.mds_id:
            errors["mds"] = "Une MDS doit être désignée pour une demande à évaluer."
        if self.circuit == self.Circuit.MDS and self.statut in statuts_apres_envoi_mds and not self.date_notification_mds:
            errors["date_notification_mds"] = "La date d'envoi à la MDS est nécessaire au calcul du délai."
        if self.date_notification_mds and self.date_reception and self.date_notification_mds < self.date_reception:
            errors["date_notification_mds"] = "L'envoi à la MDS ne peut précéder la réception de la demande."
        if self.accompagnement_autre_service and self.usager_informe_liaison and not self.date_information_usager:
            errors["date_information_usager"] = "Indiquez la date à laquelle l'usager a été informé."
        if self.montant_aide_financiere is not None and self.montant_aide_financiere < 0:
            errors["montant_aide_financiere"] = "Le montant ne peut pas être négatif."
        if errors:
            raise ValidationError(errors)

    @property
    def reference(self):
        return f"RU-{self.date_reception:%Y}-{self.pk:06d}" if self.pk else "RU (brouillon)"

    @property
    def date_echeance(self):
        """Échéance de la note : un mois calendaire ou 15 jours après notification MDS."""
        if not self.date_notification_mds:
            return None
        if self.priorite == self.Priorite.SIGNALEE:
            return self.date_notification_mds + timedelta(days=15)
        mois = self.date_notification_mds.month + 1
        annee = self.date_notification_mds.year + (1 if mois == 13 else 0)
        mois = 1 if mois == 13 else mois
        jour = min(self.date_notification_mds.day, calendar.monthrange(annee, mois)[1])
        return self.date_notification_mds.replace(year=annee, month=mois, day=jour)

    @property
    def est_cloturee(self):
        return self.statut == self.Statut.CLOTUREE

    @property
    def est_en_retard(self):
        return bool(self.date_echeance and not self.est_cloturee and self.date_echeance < timezone.localdate())

    @property
    def nombre_relances(self):
        return self.relances.count() if self.pk else 0

    def peut_etre_vu_par(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.a_la_capacite("ru_gerer_sas"):
            return True
        return bool(
            self.mds_id and self.date_notification_mds and user.a_la_capacite("peut_voir")
            and user.a_acces_mds(self.mds)
        )

    def __str__(self):
        return f"{self.reference} – {self.nom_usager} {self.prenom_usager}".strip()


class FicheRetourSAS(AuditedMixin):
    """Masque de saisie de la réponse de retour du SAS; transmis après validation du circuit."""

    REPONSE_DIRECTE = "REPONSE_DIRECTE"
    SUITE_MDS = "SUITE_MDS"
    REORIENTATION = "REORIENTATION"
    AUTRE = "AUTRE"
    TYPES_REPONSE = [
        (REPONSE_DIRECTE, "Réponse directe"),
        (SUITE_MDS, "Réponse après évaluation MDS"),
        (REORIENTATION, "Réorientation"),
        (AUTRE, "Autre suite"),
    ]
    demande = models.OneToOneField(DemandeRelationUsager, on_delete=models.CASCADE, related_name="fiche_retour_sas")
    type_reponse = models.CharField("Type de réponse / suite", max_length=20, choices=TYPES_REPONSE)
    synthese_reponse = models.TextField("Réponse à l'usager et au service émetteur")
    service_reoriente = models.CharField("Service destinataire de la réorientation", max_length=200, blank=True)
    suite_donnee = models.TextField("Suite donnée / observations", blank=True)
    date_transmission = models.DateTimeField("Date et heure de transmission", null=True, blank=True)
    transmis_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="fiches_retour_sas_transmises")

    class Meta:
        verbose_name = "Fiche retour SAS"
        verbose_name_plural = "Fiches retour SAS"

    def clean(self):
        if self.type_reponse == self.REORIENTATION and not self.service_reoriente.strip():
            raise ValidationError({"service_reoriente": "Précisez le service destinataire de la réorientation."})

    def __str__(self):
        return f"Fiche retour SAS – {self.demande.reference}"


class RelanceRU(TimestampedMixin):
    demande = models.ForeignKey(DemandeRelationUsager, on_delete=models.CASCADE, related_name="relances")
    date_relance = models.DateField("Date de la relance", default=timezone.localdate)
    commentaire = models.CharField("Commentaire", max_length=250, blank=True)
    effectuee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    transmission_direction = models.BooleanField("Transmise à la direction", default=False)

    class Meta:
        verbose_name = "Relance de demande RU"
        verbose_name_plural = "Relances de demandes RU"
        ordering = ["date_relance", "pk"]
        constraints = [models.UniqueConstraint(fields=["demande", "date_relance"], name="ru_relance_une_par_jour")]

    def __str__(self):
        return f"Relance {self.demande.reference} du {self.date_relance:%d/%m/%Y}"


class HistoriqueRU(models.Model):
    demande = models.ForeignKey(DemandeRelationUsager, on_delete=models.CASCADE, related_name="historique")
    action = models.CharField("Action", max_length=40)
    detail = models.CharField("Détail", max_length=250, blank=True)
    acteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    date_action = models.DateTimeField("Date", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Événement de suivi RU"
        verbose_name_plural = "Historique des demandes RU"
        ordering = ["-date_action", "-pk"]

    @property
    def libelle_action(self):
        libelles = {
            "CREATION": "Demande créée",
            "MISE_A_JOUR_SAISINE": "Saisine mise à jour",
            "MISE_A_JOUR_EVALUATION": "Évaluation mise à jour",
            "TRANSMISSION_SAS_MDS": "Transmission SAS vers MDS",
            "AFFECTATION_MDS": "Travailleur social affecté",
            "EVALUATION_TRANSMISE_CADRE": "Évaluation transmise au cadre",
            "VALIDATION_CADRE_MDS": "Évaluation validée par le cadre",
            "FICHE_RETOUR_SAS": "Fiche retour SAS enregistrée",
            "REPONSE_TRANSMISE": "Réponse transmise",
            "ESCALADE_DIRECTION": "Escalade à la direction",
            "RELANCE": "Relance enregistrée",
            "PIECE_AJOUTEE": "Pièce GED ajoutée",
            "COURRIER_RDV1_GENERE": "Courrier du premier rendez-vous généré",
            "COURRIER_RDV2_GENERE": "Courrier du second rendez-vous généré",
            "CADRE_NON_NOTIFIE": "Aucun cadre habilité à notifier",
        }
        return libelles.get(self.action, self.action.replace("_", " ").capitalize())

    def __str__(self):
        return f"{self.demande.reference} – {self.action}"
