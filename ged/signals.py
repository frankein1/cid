# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

"""
ged/signals.py — GED V2 CORE-DITAS
Traçabilité automatique & nettoyage SeaweedFS
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import (
    DocumentGED,
    DocumentVersion,
    HistoriqueDocument,
)
from .storage import SeaweedFSStorage

logger = logging.getLogger(__name__)

@receiver(post_save, sender=DocumentGED)
def trace_document_creation(sender, instance, created, **kwargs):
    if created:
        HistoriqueDocument.objects.create(
            document=instance,
            action="CREATION_DOCUMENT",
            utilisateur=instance.uploaded_by,
            commentaire="Création du document GED",
        )

@receiver(post_save, sender=DocumentVersion)
def trace_document_version(sender, instance, created, **kwargs):
    """
    Trace la création d’une version de document.
    """
    if created:
        HistoriqueDocument.objects.create(
            document=instance.document,
            action="CREATION_VERSION",
            utilisateur=instance.cree_par,
            commentaire=f"Ajout de la version v{instance.numero}"
        )

@receiver(post_delete, sender=DocumentVersion)
def cleanup_seaweedfs_on_delete(sender, instance, **kwargs):
    """
    SUPPRESSION PHYSIQUE CENTRALISÉE SeaweedFS
    Une version = un fichier = un fid
    """
    if not instance.seaweedfs_id:
        return

    try:
        storage = SeaweedFSStorage()
        if storage.exists(instance.seaweedfs_id):
            storage.delete(instance.seaweedfs_id)
            logger.info(
                f"SeaweedFS purge OK fid={instance.seaweedfs_id}"
            )
    except Exception as e:
        logger.error(
            f"ERREUR PURGE SeaweedFS fid={instance.seaweedfs_id} : {e}"
        )

