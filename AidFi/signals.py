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


def _envoyer(expediteur, destinataire, demande, objet, contenu, motif):
    from messagerie.models import Message, StatutLecture
    from django.contrib.contenttypes.models import ContentType
    msg = Message.objects.create(
        expediteur=expediteur,
        destinataire=destinataire,
        beneficiaire=demande.beneficiaire,
        objet=objet,
        contenu=contenu,
        motif=motif,
        priorite='importante',
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

    if demande.statut == "ACCORDEE":
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
