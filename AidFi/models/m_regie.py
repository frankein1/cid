"""
# AidFi/models/m_regie.py
Modèles RÉGIE D'URGENCE
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings  # ✅ AJOUTÉ
from .m_generique import DemandeAide

class RegieUrgence(models.Model):
    demande = models.OneToOneField(DemandeAide, on_delete=models.CASCADE, related_name='regie_urgence')
    montant_urgence = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)])
    motif_urgence = models.TextField()
    date_rendez_vous_regie = models.DateTimeField(null=True, blank=True)
    regisseur = models.CharField(max_length=200, blank=True)
    
    date_versement = models.DateTimeField(null=True, blank=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # ✅ settings.AUTH_USER_MODEL
        on_delete=models.SET_NULL, 
        null=True,
        related_name='regies_creees')  # ✅ AJOUTÉ
