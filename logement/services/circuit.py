# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/circuit.py
"""Circuit d'une demande FSL : préparation par l'agent, avis du cadre si des pièces manquent, envoi, réponse du FSL."""
from django.utils import timezone

from logement.models import DemandeFSL as D


class CircuitError(Exception):
    pass


def _message(expediteur, destinataire, demande, objet, contenu):
    from django.contrib.contenttypes.models import ContentType
    from messagerie.models import Message, StatutLecture
    if not destinataire or not destinataire.is_active or (expediteur and destinataire.pk == expediteur.pk):
        return None
    msg = Message.objects.create(
        expediteur=expediteur, destinataire=destinataire, beneficiaire=demande.beneficiaire, objet=objet[:255],
        contenu=contenu + "\n\nMessage automatique de CID.", motif='validation_cadre', priorite='importante',
        content_type=ContentType.objects.get_for_model(demande), object_id=demande.pk, reference=f"FSL-{demande.pk}")
    StatutLecture.objects.create(message=msg, utilisateur=destinataire, type_reception='destinataire')
    return msg


def _usager(demande):
    b = demande.beneficiaire
    return f"{b.prenom} {b.nom.upper()}"


def demander_avis_cadre(demande, user):
    """Toute demande FSL part avec le visa du cadre (initiales, date, signature numérisée si validée). S'il manque des
    pièces, le cadre rédige en plus la note explicative (argumentaire de pièces manquantes)."""
    if demande.statut not in (D.BROUILLON, D.AJOURNEE):
        raise CircuitError("La demande n'est pas en préparation.")
    if not demande.avis and not (demande.est_fluides and demande.instruction_administrative):
        raise CircuitError("Indiquez d'abord l'avis du travailleur social (favorable, réservé, défavorable).")
    from beneficiaire.transfert import responsable_mds
    demande.statut = D.A_VALIDER
    manque = len(demande.pieces_manquantes)
    demande.tracer(user, "Visa du cadre demandé", f"{manque} pièce(s) manquante(s)" if manque else "dossier complet")
    demande.save()
    _message(user, responsable_mds(demande.mds), demande, f"FSL : visa demandé – {_usager(demande)}",
             f"La demande FSL ({demande.get_type_aide_display().lower()}) de {_usager(demande)} attend votre visa."
             + (f" Il manque {manque} pièce(s) : rédigez la note explicative qui accompagnera le dossier." if manque else ""))


demander_visa = demander_avis_cadre


def avis_cadre(demande, cadre, accepte, note):
    if demande.statut != D.A_VALIDER:
        raise CircuitError("Aucun avis du cadre n'est attendu sur cette demande.")
    note = (note or "").strip()
    if accepte and demande.pieces_manquantes and not note:
        raise CircuitError("Des pièces manquent : la note explicative est obligatoire, elle accompagne le dossier.")
    if accepte:
        demande.cadre, demande.date_validation_cadre = cadre, timezone.now()
        demande.statut, demande.note_cadre = D.VALIDEE, note
        demande.tracer(cadre, "Visée par le cadre" + (" (pièces manquantes, note explicative)" if note else ""),
                       note[:200])
        objet = "FSL : visée par le cadre, prête à envoyer"
    else:
        demande.statut = D.BROUILLON
        demande.tracer(cadre, "Renvoyée à l'agent par le cadre", note[:200])
        objet = "FSL : demande renvoyée par le cadre"
    demande.save()
    _message(cadre, demande.cree_par, demande, f"{objet} – {_usager(demande)}", note or objet)


def envoyer(demande, user, date_envoi=None, mode=None):
    """mode : 'MAIL' ou 'IMPRIME' (compteur de papier évité) ; None = simple date d'envoi."""
    if demande.statut not in (D.VALIDEE, D.AJOURNEE):
        raise CircuitError("La demande part avec le visa du cadre : demandez-le d'abord.")
    if demande.pieces_manquantes and not demande.note_cadre:
        raise CircuitError("Des pièces manquent : le cadre doit rédiger la note explicative (demandez son visa).")
    from .fsl import SEUIL_INSTRUCTION_ADMINISTRATIVE
    if demande.est_fluides and demande.instruction_administrative:
        if demande.montant_dette > SEUIL_INSTRUCTION_ADMINISTRATIVE:
            raise CircuitError(f"Au-delà de {SEUIL_INSTRUCTION_ADMINISTRATIVE} €, l'avis d'un travailleur social est "
                               f"nécessaire : décochez « instruite par un agent administratif ».")
    elif not demande.avis:
        raise CircuitError("Indiquez l'avis du travailleur social (favorable, réservé, défavorable).")
    renvoi = demande.statut == D.AJOURNEE
    demande.statut, demande.date_envoi = D.ENVOYEE, date_envoi or timezone.localdate()
    comment = {'MAIL': " par mail", 'IMPRIME': " (imprimée pour un envoi papier)"}.get(mode, "")
    demande.tracer(user, ("Renvoyée au FSL (pièces complétées)" if renvoi else "Envoyée au FSL") + comment,
                   f"le {demande.date_envoi:%d/%m/%Y}" + (f" – {demande.gestionnaire.transmission}"
                                                         if demande.gestionnaire and demande.gestionnaire.transmission else ""))
    demande.save()


def enregistrer_reponse(demande, user, issue, date_decision, pret=None, subvention=None, garantie="", commentaire=""):
    if demande.statut != D.ENVOYEE:
        raise CircuitError("La réponse du FSL s'enregistre sur une demande envoyée.")
    if issue not in (D.ACCORDEE, D.AJOURNEE, D.REFUSEE):
        raise CircuitError("Réponse inconnue.")
    demande.statut, demande.date_decision = issue, date_decision or timezone.localdate()
    demande.montant_accorde_pret, demande.montant_accorde_subvention = pret, subvention
    demande.garantie_accordee, demande.commentaire_decision = garantie or "", commentaire or ""
    detail = []
    if pret:
        detail.append(f"prêt {pret} €")
    if subvention:
        detail.append(f"subvention {subvention} €")
    if garantie:
        detail.append(f"garantie {garantie}")
    demande.tracer(user, f"Réponse du FSL : {demande.get_statut_display().lower()}",
                   " ; ".join(detail + ([commentaire[:200]] if commentaire else [])))
    demande.save()


def abandonner(demande, user, motif=""):
    if demande.statut in (D.ACCORDEE, D.REFUSEE, D.ABANDONNEE):
        raise CircuitError("La demande est déjà close.")
    demande.statut = D.ABANDONNEE
    demande.tracer(user, "Abandonnée", motif[:200])
    demande.save()
