# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/models/m_envoi.py
from django.db import models


# ==========================================================================
# ENVOI DES DOSSIERS ET PAPIER ÉVITÉ
# ==========================================================================

class EnvoiDossier(models.Model):
    """Chaque dossier envoyé depuis CID : par mail (papier évité) ou imprimé pour un envoi papier.
    Volontairement sans l'agent : la statistique est collective (MDS, Département), jamais individuelle."""
    MAIL, IMPRIME = 'MAIL', 'IMPRIME'
    MODES = [(MAIL, "Envoi par mail"), (IMPRIME, "Imprimé pour envoi")]
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    nature = models.CharField(max_length=60, help_text="Ex. « FSL accès », « COPP »")
    mds = models.ForeignKey('mds.MDS', on_delete=models.SET_NULL, null=True, related_name='envois_dossiers')
    mode = models.CharField(max_length=8, choices=MODES)
    pages = models.PositiveIntegerField(default=0, help_text="Pages A4 (un A3 compte pour deux), pièces comprises")
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Envoi de dossier"
        verbose_name_plural = "Envois de dossiers"
        ordering = ['-date']

    def __str__(self):
        return f"{self.nature} – {self.get_mode_display()} – {self.pages} pages"
