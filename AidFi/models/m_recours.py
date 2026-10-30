# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/models/m_recours.py
"""
Recours contre un refus d'AFASE.

Le recours est une procédure externe : l'usager écrit au Président du Département (recours gracieux)
ou saisit le tribunal administratif (recours contentieux). CID n'instruit pas le recours : il en garde
la trace (date, issue) pour les statistiques et la transparence en cas de contrôle.
Si le recours aboutit, une NOUVELLE AFASE est créée à partir de la demande refusée : le premier refus
et son courrier restent intacts.
"""
from django.conf import settings
from django.db import models


class RecoursAFASE(models.Model):
    TYPES = [
        ("GRACIEUX", "Recours gracieux (Président du Département)"),
        ("CONTENTIEUX", "Recours contentieux (tribunal administratif)"),
    ]
    ISSUES = [
        ("EN_COURS", "En cours"),
        ("ACCORD", "Refus réformé : l'aide est à accorder"),
        ("REJET", "Refus confirmé"),
        ("DESISTEMENT", "Désistement de l'usager"),
    ]
    demande = models.OneToOneField("AidFi.DemandeAFASE", on_delete=models.CASCADE, related_name="recours",
                                   verbose_name="AFASE refusée")
    type_recours = models.CharField("Type de recours", max_length=12, choices=TYPES, default="GRACIEUX")
    date_recours = models.DateField("Date du recours", help_text="Date du courrier de l'usager (ou de la requête).")
    issue = models.CharField("Issue", max_length=12, choices=ISSUES, default="EN_COURS")
    date_issue = models.DateField("Date de la décision sur le recours", null=True, blank=True)
    commentaire = models.TextField("Commentaire", blank=True)
    nouvelle_demande = models.OneToOneField("AidFi.DemandeAFASE", on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name="issue_de_recours",
                                            verbose_name="Nouvelle AFASE créée suite au recours")
    enregistre_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                       related_name="+")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Recours contre un refus d'AFASE"
        verbose_name_plural = "Recours contre des refus d'AFASE"
        ordering = ["-date_recours"]

    def __str__(self):
        return f"Recours {self.get_type_recours_display().split(' (')[0].lower()} du {self.date_recours:%d/%m/%Y} " \
               f"– AFASE {self.demande_id} ({self.get_issue_display().lower()})"

    @property
    def delai_jours(self):
        return (self.date_issue - self.date_recours).days if self.date_issue else None
