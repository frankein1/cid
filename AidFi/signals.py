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

    SuiviDemande.objects.create(
        demande_id=instance.pk,
        statut_precedent=precedent or "NEANT",
        statut_nouveau=instance.statut,
        agent=getattr(instance, '_acteur', None) or instance.cree_par,
    )
    instance._statut_precedent = instance.statut
