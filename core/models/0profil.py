# core/models/profil.py

"""
Business profile defining a set of permissions
COMPLETE FIX: Nullable configuration for migrations
"""

from django.db import models
from django.contrib.auth.models import Permission, Group
from core.mixins import AuditedMixin


class Profil(AuditedMixin):
    """
    Business profile defining a set of permissions
    FIX: nullable configuration for migration compatibility
    """
    
    code = models.CharField(max_length=50, unique=True)
    
    nom = models.CharField(max_length=200)
    
    description = models.TextField(blank=True)
    
    # Associated Django permissions
    permissions = models.ManyToManyField(
        Permission,
        related_name='profils',
        blank=True,
    )
    
    # Associated Django groups
    groupes = models.ManyToManyField(
        Group,
        related_name='profils',
        blank=True,
    )
    
    # Specific business rights
    peut_creer = models.BooleanField(default=False)
    peut_instruire = models.BooleanField(default=False)
    peut_valider = models.BooleanField(default=False)
    peut_decider = models.BooleanField(default=False)
    peut_finance = models.BooleanField(default=False)
    peut_voir_stats = models.BooleanField(default=False)
    peut_administrer = models.BooleanField(default=False)
    
    
    # --- FIXED FIELDS ---
    lecture_seule = models.BooleanField(default=False) 
    
    # FIX: Make nullable temporarily for migration
    configuration = models.ForeignKey( 
        'core.Configuration', 
        on_delete=models.PROTECT,
        null=True,      # TEMPORARY: nullable for migration
        blank=True,     # TEMPORARY: blank for migration
        related_name='profil_configurations',
    )
    
    acces_donnees_sensibles = models.BooleanField(default=False)

    class Meta:
        ordering = ['nom']
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"[{self.code}] {self.nom}"
