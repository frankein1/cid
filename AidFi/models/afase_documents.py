# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/models/afase_documents.py

from django.db import models
from core.mixins import TimestampedMixin
from ged.models import DocumentGED
from .m_afase import DemandeAFASE


class DocumentAFASE(TimestampedMixin):
    """
    Association entre une demande AFASE et un document GED
    """

    TYPE_DOCUMENT_CHOICES = [
        ("IDENTITE", "Identité"),
        ("RIB", "RIB"),
        ("JUSTIFICATIF", "Justificatif"),
        ("FACTURE", "Facture"),
        ("AUTRE", "Autre"),
    ]

    demande = models.ForeignKey(
        DemandeAFASE,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    document = models.ForeignKey(
        DocumentGED,
        on_delete=models.CASCADE
    )

    type_document = models.CharField(
        max_length=20,
        choices=TYPE_DOCUMENT_CHOICES
    )

    obligatoire = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Document AFASE"
        verbose_name_plural = "Documents AFASE"
        unique_together = ("demande", "document")
