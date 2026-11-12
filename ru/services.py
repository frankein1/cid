# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/services.py
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from core.signature import initiales_utilisateur
from mds.models import UserMDSProfile
from .models import DemandeRelationUsager, FicheRetourSAS, HistoriqueRU, RelanceRU


def journaliser(demande, action, acteur=None, detail=""):
    HistoriqueRU.objects.create(demande=demande, action=action, acteur=acteur, detail=detail[:250])


def peut_gerer_sas(user):
    return bool(user.is_authenticated and (user.is_superuser or user.a_la_capacite("ru_gerer_sas")))


def peut_gerer_mds(user, demande):
    return bool(
        demande.mds_id and user.is_authenticated and user.a_la_capacite("peut_voir")
        and user.a_acces_mds(demande.mds)
    )


def est_cadre_mds(user, demande):
    return peut_gerer_mds(user, demande) and user.a_la_capacite("peut_valider")


def verifier_acces(demande, user):
    if not demande.peut_etre_vu_par(user):
        raise PermissionDenied("Cette demande est hors de votre périmètre d'accès.")


def _message_interne(expediteur, destinataire, demande, objet, contenu, motif, priorite="importante"):
    """Message interne contenant le lien et la référence, pas le récit social confidentiel."""
    if not destinataire or not destinataire.is_active or destinataire.pk == expediteur.pk:
        return None
    from messagerie.models import Message, StatutLecture
    content_type = ContentType.objects.get_for_model(DemandeRelationUsager)
    message = Message.objects.create(
        expediteur=expediteur,
        destinataire=destinataire,
        objet=objet[:255],
        contenu=contenu,
        priorite=priorite,
        motif=motif,
        reference=demande.reference,
        content_type=content_type,
        object_id=demande.pk,
        cree_par=expediteur,
    )
    StatutLecture.objects.get_or_create(message=message, utilisateur=destinataire)
    return message


def _notifier_cadre(demande, acteur):
    candidats = UserMDSProfile.objects.filter(
        mds=demande.mds, actif=True, user__is_active=True, herite_de__isnull=True,
    ).select_related("user").order_by("user__last_name", "user__first_name")
    destinataire = None
    responsable = getattr(demande.mds, "responsable", None)
    if responsable and responsable.is_active and responsable.a_la_capacite("peut_valider") and responsable.a_acces_mds(demande.mds):
        destinataire = responsable
    if not destinataire:
        destinataire = next((p.user for p in candidats if p.user.pk != acteur.pk and p.user.a_la_capacite("peut_valider")), None)
    if not destinataire:
        return None
    if destinataire:
        _message_interne(
            acteur, destinataire, demande, f"RU {demande.reference} à valider",
            f"Une évaluation RU est transmise pour validation du cadre. Référence : {demande.reference}.\n"
            f"Ouvrir le dossier : /ru/{demande.pk}/",
            "validation_cadre", "urgente" if demande.priorite == DemandeRelationUsager.Priorite.SIGNALEE else "importante",
        )
    return destinataire


def _notifier_sas(demande, acteur):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    destinataires = User.objects.filter(
        is_active=True, profils__actif=True, profils__capacites__code="ru_gerer_sas"
    ).distinct().order_by("last_name", "first_name")
    for destinataire in destinataires:
        _message_interne(
            acteur, destinataire, demande, f"RU {demande.reference} à finaliser par le SAS",
            f"L'évaluation sociale de la demande {demande.reference} a été validée par le cadre MDS.\n"
            f"Ouvrir le dossier et compléter la fiche retour SAS : /ru/{demande.pk}/",
            "transmission_info", "urgente" if demande.priorite == DemandeRelationUsager.Priorite.SIGNALEE else "importante",
        )


def _notifier_direction(demande, acteur):
    """Escalade une troisième relance au responsable MDS, avec repli sur un cadre habilité."""
    if not demande.mds_id:
        return None
    destinataire = getattr(demande.mds, "responsable", None)
    if not (destinataire and destinataire.is_active and destinataire.pk != acteur.pk
            and destinataire.a_la_capacite("peut_valider") and destinataire.a_acces_mds(demande.mds)):
        destinataire = next((
            profil.user for profil in UserMDSProfile.objects.filter(
                mds=demande.mds, actif=True, user__is_active=True, herite_de__isnull=True,
            ).select_related("user").order_by("user__last_name", "user__first_name")
            if profil.user.pk != acteur.pk and profil.user.a_la_capacite("peut_valider")
        ), None)
    if not destinataire:
        return None
    _message_interne(
        acteur, destinataire, demande, f"Escalade RU {demande.reference} après trois relances",
        f"La demande {demande.reference} dépasse son délai malgré trois relances.\n"
        f"Référence : {demande.reference} · Échéance : {demande.date_echeance:%d/%m/%Y}.\n"
        f"Ouvrir le dossier dans CID : /ru/{demande.pk}/",
        "signalement", "urgente",
    )
    return destinataire


def verifier_evaluation_complete(demande):
    manquants = []
    if not demande.elements_declaratifs.strip():
        manquants.append("les éléments déclaratifs de l'usager")
    if not demande.evaluation_sociale.strip():
        manquants.append("l'évaluation sociale synthétique")
    if not demande.modalites_contact.strip():
        manquants.append("les contacts et démarches réalisés")
    if not demande.situation_actualisee.strip():
        manquants.append("la situation actualisée")
    if not demande.problematique_plan.strip():
        manquants.append("la problématique repérée / le plan préconisé du TERU")
    if demande.absence_premier_rendez_vous and not demande.date_second_rendez_vous:
        manquants.append("la date du second rendez-vous proposé")
    if demande.aide_financiere_proposee and not demande.decision_aide_financiere.strip():
        manquants.append("la décision relative à l'aide financière")
    if demande.aide_financiere_proposee and demande.montant_aide_financiere is None:
        manquants.append("le montant de l'aide financière proposée")
    if not demande.aide_financiere_proposee and demande.decision_aide_financiere and not demande.motif_rejet_aide.strip():
        manquants.append("le motif du rejet de l'aide")
    if manquants:
        raise ValidationError("Complétez " + ", ".join(manquants) + " avant la transmission au cadre.")


@transaction.atomic
def transmettre_sas_vers_mds(demande, mds, agent, acteur):
    verifier_acces(demande, acteur)
    if not peut_gerer_sas(acteur):
        raise PermissionDenied("Seul un agent SAS peut transmettre une demande à une MDS.")
    if demande.circuit != DemandeRelationUsager.Circuit.MDS or demande.statut != DemandeRelationUsager.Statut.A_TRAITER_SAS:
        raise ValidationError("Cette demande n'est pas en attente d'une transmission SAS vers MDS.")
    if demande.date_reception > timezone.localdate():
        raise ValidationError("Une demande dont la réception est dans le futur ne peut pas être transmise.")
    if not mds or not mds.active or not agent or not agent.is_active:
        raise ValidationError("Choisissez une MDS active et un travailleur social actif.")
    if not UserMDSProfile.objects.filter(user=agent, mds=mds, actif=True, herite_de__isnull=True).exists():
        raise ValidationError("Le travailleur social doit être rattaché directement à la MDS choisie.")
    demande.mds = mds
    demande.agent_assigne = agent
    demande.date_notification_mds = timezone.localdate()
    demande.statut = DemandeRelationUsager.Statut.EN_EVALUATION
    demande.save(update_fields=["mds", "agent_assigne", "date_notification_mds", "statut", "updated_at"])
    journaliser(demande, "TRANSMISSION_SAS_MDS", acteur, f"Envoyée à {agent.get_full_name()} – {mds.nom}")
    _message_interne(
        acteur, agent, demande, f"Nouvelle demande RU {demande.reference}",
        f"Le SAS vous transmet une demande d'évaluation sociale à traiter.\n"
        f"Référence : {demande.reference} · Priorité : {demande.get_priorite_display()} · Échéance : {demande.date_echeance:%d/%m/%Y}.\n"
        f"Ouvrir le dossier dans CID : /ru/{demande.pk}/",
        "demande_beneficiaire", "urgente" if demande.priorite == DemandeRelationUsager.Priorite.SIGNALEE else "importante",
    )


@transaction.atomic
def affecter_a_un_travailleur(demande, agent, acteur):
    verifier_acces(demande, acteur)
    if not est_cadre_mds(acteur, demande):
        raise PermissionDenied("Seul un cadre autorisé de la MDS peut désigner le travailleur social.")
    if demande.statut not in (DemandeRelationUsager.Statut.A_TRAITER_MDS, DemandeRelationUsager.Statut.EN_EVALUATION):
        raise ValidationError("Cette demande n'est pas en attente d'affectation.")
    if not agent or not agent.is_active or not UserMDSProfile.objects.filter(
        user=agent, mds=demande.mds, actif=True, herite_de__isnull=True
    ).exists():
        raise ValidationError("Le travailleur social doit être actif et rattaché à cette MDS.")
    demande.agent_assigne = agent
    demande.statut = DemandeRelationUsager.Statut.EN_EVALUATION
    demande.save(update_fields=["agent_assigne", "statut", "updated_at"])
    journaliser(demande, "AFFECTATION_MDS", acteur, f"Affectation à {agent.get_full_name()}")
    _message_interne(
        acteur, agent, demande, f"Demande RU {demande.reference} affectée",
        f"Votre cadre vous affecte la demande {demande.reference}.\nOuvrir le dossier dans CID : /ru/{demande.pk}/",
        "suivi_dossier", "urgente" if demande.priorite == DemandeRelationUsager.Priorite.SIGNALEE else "importante",
    )


@transaction.atomic
def soumettre_evaluation(demande, acteur):
    verifier_acces(demande, acteur)
    if not (demande.agent_assigne_id == acteur.pk or est_cadre_mds(acteur, demande)):
        raise PermissionDenied("Seul le travailleur chargé du dossier ou un cadre de la MDS peut transmettre l'évaluation.")
    if demande.statut != DemandeRelationUsager.Statut.EN_EVALUATION:
        raise ValidationError("L'évaluation n'est pas dans un état permettant sa transmission.")
    verifier_evaluation_complete(demande)
    demande.statut = DemandeRelationUsager.Statut.A_VALIDER_CADRE
    demande.date_soumission_mds = timezone.now()
    demande.save(update_fields=["statut", "date_soumission_mds", "updated_at"])
    journaliser(demande, "EVALUATION_TRANSMISE_CADRE", acteur)
    if not _notifier_cadre(demande, acteur):
        journaliser(demande, "CADRE_NON_NOTIFIE", acteur, "Aucun cadre habilité trouvé dans la MDS : à signaler à la direction")


@transaction.atomic
def valider_evaluation(demande, acteur):
    verifier_acces(demande, acteur)
    if not est_cadre_mds(acteur, demande):
        raise PermissionDenied("La validation est réservée à un cadre autorisé de la MDS.")
    if demande.statut != DemandeRelationUsager.Statut.A_VALIDER_CADRE:
        raise ValidationError("La demande n'est pas en attente de validation du cadre.")
    verifier_evaluation_complete(demande)
    demande.statut = DemandeRelationUsager.Statut.A_VALIDER_SAS
    demande.validee_par = acteur
    demande.initiales_signature_cadre = initiales_utilisateur(acteur)
    demande.date_validation_mds = timezone.now()
    demande.save(update_fields=["statut", "validee_par", "initiales_signature_cadre", "date_validation_mds", "updated_at"])
    journaliser(demande, "VALIDATION_CADRE_MDS", acteur, f"Signature {demande.initiales_signature_cadre} · {demande.date_validation_mds:%d/%m/%Y %H:%M}")
    _notifier_sas(demande, acteur)


@transaction.atomic
def transmettre_reponse(demande, acteur):
    verifier_acces(demande, acteur)
    if not peut_gerer_sas(acteur):
        raise PermissionDenied("La transmission finale de la réponse est réservée au SAS.")
    if demande.circuit == DemandeRelationUsager.Circuit.MDS and demande.statut != DemandeRelationUsager.Statut.A_VALIDER_SAS:
        raise ValidationError("La réponse doit d'abord être validée par le cadre MDS.")
    if demande.circuit == DemandeRelationUsager.Circuit.SAS and demande.statut != DemandeRelationUsager.Statut.A_TRAITER_SAS:
        raise ValidationError("Cette demande n'est pas en attente de réponse directe du SAS.")
    fiche = FicheRetourSAS.objects.select_for_update().filter(demande=demande).first()
    if not fiche:
        raise ValidationError("Complétez d'abord la fiche de retour SAS.")
    fiche.full_clean()
    if not fiche.synthese_reponse.strip():
        raise ValidationError("Saisissez la réponse à transmettre.")
    if demande.circuit == DemandeRelationUsager.Circuit.MDS and not demande.usager_informe_transmission:
        raise ValidationError("Confirmez que l'usager a été informé des éléments transmis.")
    now = timezone.now()
    demande.statut = DemandeRelationUsager.Statut.CLOTUREE
    demande.date_reponse_transmise = now
    demande.reponse_transmise_par = acteur
    demande.save(update_fields=["statut", "date_reponse_transmise", "reponse_transmise_par", "updated_at"])
    fiche.date_transmission = now
    fiche.transmis_par = acteur
    fiche.save(update_fields=["date_transmission", "transmis_par", "updated_at", "modifie_par"])
    journaliser(demande, "REPONSE_TRANSMISE", acteur, "Transmission SAS à l'usager et au service émetteur enregistrée dans CID")


@transaction.atomic
def relancer(demande, acteur, commentaire=""):
    verifier_acces(demande, acteur)
    if not peut_gerer_sas(acteur):
        raise PermissionDenied("Seul le SAS peut enregistrer une relance.")
    if demande.est_cloturee:
        raise ValidationError("Une demande clôturée ne peut pas être relancée.")
    if not demande.est_en_retard:
        raise ValidationError("La procédure prévoit une relance pour les demandes hors délai.")
    date = timezone.localdate()
    if demande.relances.filter(date_relance=date).exists():
        raise ValidationError("Une relance a déjà été enregistrée aujourd'hui.")
    rang = demande.relances.count() + 1
    escalade = rang >= 3 and not demande.date_escalade_direction
    RelanceRU.objects.create(
        demande=demande, date_relance=date, commentaire=commentaire,
        effectuee_par=acteur, transmission_direction=escalade,
    )
    if escalade:
        demande.date_escalade_direction = timezone.now()
        demande.save(update_fields=["date_escalade_direction", "updated_at"])
    destinataire_direction = _notifier_direction(demande, acteur) if escalade else None
    journaliser(
        demande, "ESCALADE_DIRECTION" if escalade else "RELANCE", acteur,
        (f"3e relance : message interne envoyé à {destinataire_direction.get_full_name()}"
         if destinataire_direction else "3e relance : escalade tracée, destinataire de direction non identifié")
        if escalade else f"Relance n°{rang}",
    )
