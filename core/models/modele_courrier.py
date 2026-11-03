# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/models/modele_courrier.py
"""
Texte d'un courrier produit par CID, modifiable en administration (voir core/courriers/registre.py).
Une ligne par courrier ; sans ligne, CID utilise le texte par défaut du registre.
"""
from django.conf import settings
from django.db import models


class ModeleCourrier(models.Model):
    code = models.CharField("Courrier", max_length=50, unique=True)
    objet = models.CharField("Objet", max_length=300, blank=True)
    corps = models.TextField("Texte du courrier", blank=True)
    signature = models.TextField("Signature", blank=True)
    modifie_le = models.DateTimeField("Modifié le", auto_now=True)
    modifie_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="+", verbose_name="Modifié par")

    class Meta:
        verbose_name = "Modèle de courrier"
        verbose_name_plural = "Modèles de courriers"
        ordering = ["code"]

    def __str__(self):
        from core.courriers.registre import COURRIERS
        d = COURRIERS.get(self.code)
        return d["libelle"] if d else self.code

    @property
    def definition(self):
        from core.courriers.registre import COURRIERS
        return COURRIERS.get(self.code)

    def est_modifie(self):
        d = self.definition
        return bool(d) and any((getattr(self, c) or "") != (d.get(c) or "") for c in ("objet", "corps", "signature"))
    est_modifie.boolean = True
    est_modifie.short_description = "Texte modifié"

    def remettre_texte_origine(self):
        d = self.definition
        for c in ("objet", "corps", "signature"):
            setattr(self, c, d.get(c, ""))

    @classmethod
    def creer_manquants(cls):
        """Une ligne (texte par défaut) pour chaque courrier du registre qui n'en a pas encore."""
        from core.courriers.registre import COURRIERS
        existants = set(cls.objects.values_list("code", flat=True))
        for code, d in COURRIERS.items():
            if code not in existants:
                cls.objects.create(code=code, objet=d.get("objet", ""), corps=d.get("corps", ""),
                                   signature=d.get("signature", ""))
