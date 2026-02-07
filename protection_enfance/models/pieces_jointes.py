from django.db import models
from .informations_preoccupantes import InformationPreoccupante


class PieceJointe(models.Model):
information = models.ForeignKey(InformationPreoccupante, related_name='pieces_jointes', on_delete=models.CASCADE)
fichier = models.FileField(upload_to='ip_pieces/%Y/%m/%d')
nom = models.CharField(max_length=255, blank=True)
uploaded_at = models.DateTimeField(auto_now_add=True)
