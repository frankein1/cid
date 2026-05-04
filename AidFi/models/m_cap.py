# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/models/m_cap.py
from django.db import models
from django.conf import settings
from .m_generique import DemandeAide

class CAPCheque(models.Model):
    demande = models.OneToOneField(DemandeAide, on_delete=models.CASCADE, related_name='cap_cheque')
    numero_cheque = models.CharField(max_length=50, unique=True)
    montant = models.DecimalField(max_digits=8, decimal_places=2)
    date_emission = models.DateField()
    date_envoi = models.DateField(null=True, blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='caps_creees')
    
    def __str__(self):
        return f"CAP {self.numero_cheque} - {self.demande.beneficiaire}"
