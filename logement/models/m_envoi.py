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
    pages = models.PositiveIntegerField(default=0, help_text="Total compté : dossier + pièces jointes")
    pages_dossier = models.PositiveIntegerField(default=0, help_text="Pages du dossier lui-même (minimum du CSV ou réel)")
    pages_pieces = models.PositiveIntegerField(default=0, help_text="Pages des pièces jointes (minimum du CSV ou réel)")
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Envoi de dossier"
        verbose_name_plural = "Envois de dossiers"
        ordering = ['-date']

    def __str__(self):
        return f"{self.nature} – {self.get_mode_display()} – {self.pages} pages"


class ReglePagesEnvoi(models.Model):
    """Minimum de pages par type de dossier, chargé depuis un fichier CSV (commande importer_pages_envois) :
    pages du dossier, et pages de l'ensemble des pièces jointes. Le compteur retient le plus grand entre ce minimum
    et les pages réellement économisées."""
    code = models.CharField(max_length=40, unique=True, help_text="Ex. AFASE, FSL, COPP")
    libelle = models.CharField(max_length=160)
    pages_dossier = models.PositiveIntegerField(default=0)
    pages_pieces_jointes = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Minimum de pages par type de dossier"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} : dossier {self.pages_dossier} p., pièces {self.pages_pieces_jointes} p."
