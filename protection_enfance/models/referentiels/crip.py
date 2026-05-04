# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/models/referentiels/crip.py
from django.db import models
from core.mixins import TimestampedMixin

class CRIP(TimestampedMixin):
    """Cellule Départementale de Recueil des Informations Préoccupantes"""
    nom = models.CharField(max_length=200, default="CRIP CD13")
    telephone = models.CharField(max_length=20, default="04 13 31 80 80")
    email = models.EmailField(default="crip@departement13.fr")
    adresse = models.TextField(default="52 avenue de Saint-Just - 13256 Marseille")
    
    responsable = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return self.nom
