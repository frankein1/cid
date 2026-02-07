# core/models/organisation.py

"""
Organizational models
"""

from django.db import models
from core.mixins import AuditedMixin
from django.contrib.auth import get_user_model


class Service(AuditedMixin):
    """
    Organizational unit (SAPM, SL, SAS)
    """
    
    TYPES_SERVICE = [
        ('CENTRAL', 'Central service'),
        ('SUPPORT', 'Support service'),
        ('TERRITOIRE', 'Territorial service'),
    ]
    
    code = models.CharField(
        max_length=20,
        unique=True,
    )
    
    nom = models.CharField(max_length=200)
    
    type_service = models.CharField(
        max_length=20,
        choices=TYPES_SERVICE,
        default='CENTRAL',
    )
    
    service_parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services_enfants',
    )
    
    direction = models.CharField(
        max_length=100,
        choices=[
            ('DITAS', 'DITAS - Direction of Territories and Social Action'),
            ('DEF', 'DEF - Child-Family Direction'),
        ],
    )
    
    adresse = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(max_length=100, blank=True)
    contact_telephone = models.CharField(max_length=20, blank=True)
    
    # Other information
    commentaire = models.TextField(blank=True)
    responsable_designation = models.CharField(max_length=100, blank=True)
    
    # Status
    actif = models.BooleanField(default=True)
    
    # Display order
    ordre = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['ordre', 'nom']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['type_service', 'actif']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.nom}"
    
    def get_agents_actifs(self):
        """Return all active agents in the service"""
        User = get_user_model()
        return User.objects.filter(
            service_principal=self,
            is_active=True
        )
    
    def get_hierarchie(self):
        """Return service hierarchy"""
        hierarchie = [self]
        parent = self.service_parent
        while parent:
            hierarchie.insert(0, parent)
            parent = parent.service_parent
        return hierarchie
