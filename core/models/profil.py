# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# core/models/profil.py

from django.db import models
from core.mixins import AuditedMixin
from core.models.capacite import Capacite


class Profil(AuditedMixin):
    """
    Profil RH / fonctionnel.
    Sert uniquement à attribuer des capacités métier.
    """

    code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Code du profil (ex: MDS_Cadres, DITAS_Direction)"
    )

    nom = models.CharField(max_length=150)

    description = models.TextField(blank=True)

    capacites = models.ManyToManyField(
        Capacite,
        blank=True,
        related_name="profils",
        help_text="Capacités accordées par ce profil"
    )

    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profils"
        ordering = ["code"]

    def __str__(self):
        return self.nom

