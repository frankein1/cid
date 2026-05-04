# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

#core/models/capacite.py

from django.db import models


class Capacite(models.Model):
    """
    Capacité métier atomique.
    Une capacité représente une action fonctionnelle possible,
    indépendante du périmètre (MDS, DITAS, global).
    """

    code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Code technique stable (snake_case)"
    )

    nom = models.CharField(
        max_length=150,
        help_text="Nom lisible (interface / admin)"
    )

    description = models.TextField(blank=True)

    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Capacité"
        verbose_name_plural = "Capacités"
        ordering = ["code"]

    def __str__(self):
        return self.nom
