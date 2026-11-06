# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/models/proconnect.py
"""Lien entre un compte CID et une identité ProConnect (voir core/proconnect.py)."""
from django.conf import settings
from django.db import models


class IdentiteProConnect(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="identites_proconnect")
    sub = models.CharField("Identifiant ProConnect (sub)", max_length=255)
    idp_id = models.CharField("Fournisseur d'identité", max_length=255, blank=True)
    siret = models.CharField("SIRET de la structure", max_length=14, blank=True)
    courriel = models.EmailField(blank=True)
    date_lien = models.DateTimeField(auto_now_add=True)
    derniere_connexion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Identité ProConnect"
        verbose_name_plural = "Identités ProConnect"
        constraints = [models.UniqueConstraint(fields=["sub", "idp_id"], name="identite_proconnect_unique")]

    def __str__(self):
        return f"{self.user} ← ProConnect ({self.courriel})"
