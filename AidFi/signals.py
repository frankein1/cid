# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/signals.py
"""
Journal des statuts des demandes d'aide (SuiviDemande).

- Écoute TOUTES les demandes (DemandeAide et ses sous-types : DemandeAFASE...).
  Avec l'héritage Django, une DemandeAFASE envoie le signal sous son propre
  nom : écouter seulement DemandeAide ne suffisait pas.
- Une ligne par création et par changement de statut, jamais modifiée.
- L'auteur est l'agent connecté : la vue le transmet via demande._acteur ;
  à défaut, le créateur de la demande.
- Au dépôt (statut DEPOSEE), le responsable de la MDS est prévenu par la
  messagerie CID (même règle que pour les transferts : adjoint prévention,
  sinon responsable de MDS, sinon directeur de la fiche MDS).
- Quand le cadre répond (accord, refus, ajournement, retour en instruction),
  l'agent qui avait déposé la demande est prévenu.
- Chaque message est rattaché à la demande : la messagerie affiche un bouton
  « Ouvrir le dossier » (les droits restent vérifiés à l'ouverture).
- CAP : messages en priorité « urgente » ; si la remise passe par la paierie,
  les régisseurs centraux sont prévenus.
"""

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from AidFi.models.m_generique import DemandeAide, SuiviDemande


def _est_demande(instance):
    return isinstance(instance, DemandeAide)


@receiver(pre_save)
def memoriser_statut_precedent(sender, instance, **kwargs):
    """Avant l'enregistrement : on retient le statut en base."""
    if not _est_demande(instance):
        return
    if instance.pk:
        instance._statut_precedent = (
            DemandeAide.objects.filter(pk=instance.pk)
            .values_list('statut', flat=True).first()
        )
    else:
        instance._statut_precedent = None


@receiver(post_save)
def journaliser_statut(sender, instance, created, **kwargs):
    """Après l'enregistrement : une ligne de suivi si le statut a changé."""
    if not _est_demande(instance):
        return
    # Un sous-type (AFASE) déclenche aussi la sauvegarde de sa partie parente :
    # on ne journalise qu'une fois, sur le type réel de la demande.
    if sender is not type(instance):
        return

    precedent = getattr(instance, '_statut_precedent', None)
    if not created and precedent == instance.statut:
        return

    acteur = getattr(instance, '_acteur', None) or instance.cree_par
    SuiviDemande.objects.create(
        demande_id=instance.pk,
        statut_precedent=precedent or "NEANT",
        statut_nouveau=instance.statut,
        agent=acteur,
    )
    instance._statut_precedent = instance.statut

    if instance.statut == "DEPOSEE":
        prevenir_depot(instance, acteur)
    elif precedent == "DEPOSEE":
        prevenir_reponse_cadre(instance, acteur)


def _est_cap(demande):
    from AidFi.models.m_cap import DemandeCAP
    return isinstance(demande, DemandeCAP)


def _est_regie(demande):
    from AidFi.models.m_regie import DemandeRegie
    return isinstance(demande, DemandeRegie)


def _versement_regie(demande):
    """« 150 € en espèces » ou « 150 € versés à Hôtel X (facture F-12) »."""
    if demande.mode_paiement == 'TIERS':
        ref = f" (facture {demande.tiers_reference})" if demande.tiers_reference else ""
        return f"{demande.montant_accorde} € versés à {demande.tiers_nom}{ref}"
    return f"{demande.montant_accorde} € en espèces"


def _envoyer(expediteur, destinataire, demande, objet, contenu, motif, priorite=None):
    from messagerie.models import Message, StatutLecture
    from django.contrib.contenttypes.models import ContentType
    msg = Message.objects.create(
        expediteur=expediteur,
        destinataire=destinataire,
        beneficiaire=demande.beneficiaire,
        objet=objet,
        contenu=contenu,
        motif=motif,
        priorite=priorite or ('urgente' if _est_cap(demande) or _est_regie(demande) else 'importante'),
        content_type=ContentType.objects.get_for_model(demande),
        object_id=demande.pk,
        reference=f"AIDE-{demande.pk}",
    )
    StatutLecture.objects.create(message=msg, utilisateur=destinataire, type_reception='destinataire')
    return msg


def prevenir_reponse_cadre(demande, cadre):
    """Message CID à l'agent qui avait déposé la demande : le cadre a répondu."""
    depot = (SuiviDemande.objects
             .filter(demande_id=demande.pk, statut_nouveau="DEPOSEE")
             .order_by('-id').first())
    agent = (depot.agent if depot and depot.agent else None) or demande.cree_par
    if not agent or not cadre or agent == cadre:
        return

    benef = demande.beneficiaire
    type_aide = demande.type_aide.nom if demande.type_aide else "Aide financière"
    decision = getattr(demande, 'decision', None)

    if _est_cap(demande) and demande.statut == "ACCORDEE":
        resultat = (f"ACCORDÉE : {demande.montant_accorde} € en chèques service, "
                    f"à retirer auprès de {cadre.get_full_name() or cadre.username}")
    elif _est_regie(demande) and demande.statut == "TRANSMISE_PAIERIE":
        resultat = (f"ACCORDÉE : {_versement_regie(demande)}, "
                    f"transmise à la régie centrale (versement sous 24 h)")
        prevenir_regie_centrale(demande, cadre)
    elif demande.statut == "TRANSMISE_PAIERIE":
        resultat = (f"ACCORDÉE : {demande.montant_accorde} € en chèques service, "
                    f"remise par la paierie départementale (dossier transmis au régisseur central)")
        prevenir_regie_centrale(demande, cadre)
    elif demande.statut == "ACCORDEE":
        resultat = "ACCORDÉE"
        if decision and decision.montant_accorde:
            resultat += f" : {decision.montant_accorde} € pour {decision.duree_accordee} mois"
    elif demande.statut == "REFUSEE":
        resultat = "REFUSÉE"
    elif demande.statut == "AJO":
        resultat = "AJOURNÉE : le dossier vous revient pour être complété"
    elif demande.statut == "EN_INSTRUCTION":
        resultat = "RETOURNÉE EN INSTRUCTION : le dossier vous revient pour être complété"
    else:
        resultat = demande.statut

    motivation = ""
    if decision and decision.motivation and demande.statut in ("ACCORDEE", "REFUSEE", "AJO"):
        motivation = f"\nMotivation : {decision.motivation}\n"
    if (_est_cap(demande) or _est_regie(demande)) and demande.statut == "REFUSEE" and demande.motif_refus:
        motivation = f"\nMotif : {demande.motif_refus}\n"

    _envoyer(
        cadre, agent, demande,
        objet=f"Réponse du cadre - {type_aide} : {benef.prenom} {benef.nom.upper()} (dossier {demande.pk})",
        contenu=(
            f"La demande n° {demande.pk} ({type_aide}) pour {benef.prenom} {benef.nom.upper()} "
            f"est {resultat}.\n{motivation}\n"
            f"Réponse de : {cadre.get_full_name() or cadre.username}.\n"
            f"Message automatique de CID."
        ),
        motif='suivi_dossier',
    )


def prevenir_depot(demande, acteur):
    """Message CID au responsable de la MDS : une demande attend sa décision."""
    from beneficiaire.transfert import responsable_mds

    if getattr(demande, 'decision_inspecteur', False):
        prevenir_inspecteurs(demande, acteur)
        return
    responsable = responsable_mds(demande.mds)
    if not responsable or not acteur or responsable == acteur:
        return

    benef = demande.beneficiaire
    type_aide = demande.type_aide.nom if demande.type_aide else "Aide financière"
    _envoyer(
        acteur, responsable, demande,
        objet=f"{type_aide} à décider : {benef.prenom} {benef.nom.upper()} (dossier {demande.pk})",
        contenu=(
            f"La demande n° {demande.pk} ({type_aide}) pour {benef.prenom} {benef.nom.upper()} "
            f"a été déposée et attend votre décision.\n\n"
            f"Déposée par : {acteur.get_full_name() or acteur.username}.\n"
            f"Message automatique de CID."
        ),
        motif='validation_cadre',
    )


def prevenir_inspecteurs(demande, acteur):
    """AFASE d'une famille avec une mesure ASE : la décision revient à l'inspecteur enfance-famille."""
    from core.models import User
    benef = demande.beneficiaire
    for inspecteur in User.objects.filter(is_active=True, profils__code='PIEF', profils__actif=True).distinct():
        if acteur and inspecteur.pk == acteur.pk:
            continue
        _envoyer(
            acteur, inspecteur, demande,
            objet=f"AFASE à décider (mesure ASE) : {benef.prenom} {benef.nom.upper()} (dossier {demande.pk})",
            contenu=(
                f"La demande d'AFASE n° {demande.pk} pour {benef.prenom} {benef.nom.upper()} ({demande.mds}) "
                f"concerne une famille avec une mesure ASE ({demande.get_mesure_ase_display().lower()}) : "
                f"elle attend votre décision.\n\nDéposée par : {acteur.get_full_name() or acteur.username}.\n"
                f"Message automatique de CID."
            ),
            motif='validation_cadre',
        )


def prevenir_regie_centrale(demande, cadre):
    """CAP remis par la paierie, ou régie d'urgence accordée : message à chaque régisseur central."""
    from core.models import User
    benef = demande.beneficiaire
    for regisseur in User.objects.filter(is_active=True, profils__code='REGISSEUR_CENTRAL',
                                         profils__actif=True).distinct():
        if _est_regie(demande):
            _envoyer(
                cadre, regisseur, demande,
                objet=f"Régie d'urgence à verser sous 24 h : {benef.prenom} {benef.nom.upper()} (dossier {demande.pk})",
                contenu=(
                    f"Une régie d'urgence a été accordée par {demande.mds} "
                    f"pour {benef.prenom} {benef.nom.upper()} : {_versement_regie(demande)}.\n"
                    + ("La facture et le RIB du tiers sont joints au dossier.\n" if demande.mode_paiement == 'TIERS' else "")
                    + f"Le versement doit intervenir dans les 24 heures.\n\n"
                    f"Décision de : {cadre.get_full_name() or cadre.username}.\n"
                    f"Message automatique de CID."
                ),
                motif='validation_cadre',
            )
            continue
        _envoyer(
            cadre, regisseur, demande,
            objet=f"CAP à remettre en paierie : {benef.prenom} {benef.nom.upper()} (dossier {demande.pk})",
            contenu=(
                f"Une demande de chèques service a été accordée par {demande.mds} "
                f"pour {benef.prenom} {benef.nom.upper()} : {demande.montant_accorde} €.\n"
                f"La remise doit avoir lieu à la paierie départementale.\n\n"
                f"Décision de : {cadre.get_full_name() or cadre.username}.\n"
                f"Message automatique de CID."
            ),
            motif='validation_cadre',
        )



def prevenir_versement_regie(demande, regisseur):
    """Régie d'urgence versée : message à l'AS qui a déposé la demande et au cadre qui l'a accordée."""
    from django.utils import timezone
    depot = SuiviDemande.objects.filter(demande_id=demande.pk, statut_nouveau="DEPOSEE").order_by('-id').first()
    agent = (depot.agent if depot and depot.agent else None) or demande.cree_par
    benef = demande.beneficiaire
    qui = regisseur.get_full_name() or regisseur.username
    comment = f"à {demande.tiers_nom}" if demande.mode_paiement == 'TIERS' else "en espèces"
    partiel = (f" (sur {demande.montant_accorde} € accordés)" if demande.montant_verse != demande.montant_accorde else "")
    for destinataire in {u for u in (agent, demande.decide_par) if u and u.pk != regisseur.pk}:
        _envoyer(
            regisseur, destinataire, demande,
            objet=f"Régie d'urgence versée : {benef.prenom} {benef.nom.upper()} (dossier {demande.pk})",
            contenu=(f"La régie d'urgence pour {benef.prenom} {benef.nom.upper()} a été versée {comment} le "
                     f"{timezone.localtime(demande.date_versement):%d/%m/%Y à %H:%M} : "
                     f"{demande.montant_verse} €{partiel}.\n"
                     + (f"N° d'enregistrement comptable : {demande.reference_comptable}.\n" if demande.reference_comptable else "")
                     + f"Le dossier n° {demande.pk} est clôturé par {qui}.\n\nMessage automatique de CID."),
            motif='suivi_dossier',
        )
