# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/models/conservation.py
"""Durée de conservation d'un traitement, importée depuis le tableau rempli par le DPO (voir core/conservation.py)."""
from django.conf import settings
from django.db import models


class DureeConservation(models.Model):
    code = models.CharField("Traitement", max_length=40, unique=True)
    base_active_mois = models.PositiveSmallIntegerField("Base active (mois)", null=True, blank=True)
    point_de_depart = models.CharField("Point de départ", max_length=200, blank=True)
    archivage_mois = models.PositiveSmallIntegerField("Archivage intermédiaire (mois)", null=True, blank=True)
    sort_final = models.CharField("Sort final", max_length=15, blank=True,
                                  choices=[("SUPPRESSION", "Suppression"), ("ANONYMISATION", "Anonymisation"),
                                           ("ARCHIVES", "Versement aux archives départementales")])
    reference = models.TextField("Base légale ou référence", blank=True)
    commentaire = models.TextField("Commentaire du DPO", blank=True)
    importe_le = models.DateTimeField("Importé le", auto_now=True)
    importe_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='+', verbose_name="Importé par")

    class Meta:
        verbose_name = "Durée de conservation (RGPD)"
        verbose_name_plural = "Durées de conservation (RGPD)"
        ordering = ['code']

    def __str__(self):
        from core.conservation import PAR_CODE
        t = PAR_CODE.get(self.code)
        return t[1] if t else self.code
