# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# core/models/configuration.py

from django.db import models
from django.conf import settings
import json
from datetime import datetime, date

class Configuration(models.Model):
    """
    Global system configuration (key-value)
    Parameters modifiable without redeployment
    """
    
    TYPES = [
        ('STRING', 'String'),
        ('INTEGER', 'Integer'),
        ('FLOAT', 'Float'),
        ('BOOLEAN', 'Boolean'),
        ('JSON', 'JSON'),
        ('DATE', 'Date'),
        ('DATETIME', 'Datetime'),
    ]
    
    cle = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique parameter identifier"
    )
    
    valeur = models.TextField(
        help_text="Parameter value (stored as text)"
    )
    
    type_valeur = models.CharField(
        max_length=20,
        choices=TYPES,
        default='STRING',
    )
    
    description = models.TextField(blank=True)
    
    categorie = models.CharField(
        max_length=100,
        help_text="Logical grouping (SYSTEM, SECURITY, BUSINESS, etc.)"
    )
    
    modifiable = models.BooleanField(
        default=True,
        help_text="Can be modified via the interface"
    )
    
    # Audit
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['categorie', 'cle']
    
    def __str__(self):
        return f"{self.cle} = {self.valeur}"
    
    def get_valeur_typee(self):
        """Return value with correct Python type (with error handling)"""
        if self.type_valeur == 'INTEGER':
            try:
                return int(self.valeur)
            except ValueError:
                return None
        elif self.type_valeur == 'FLOAT':
            try:
                return float(self.valeur)
            except ValueError:
                return None
        elif self.type_valeur == 'BOOLEAN':
            return self.valeur.lower() in ('true', '1', 't', 'y', 'yes', 'vrai', 'oui') 
        elif self.type_valeur == 'JSON':
            try:
                return json.loads(self.valeur)
            except json.JSONDecodeError:
                return {}
        elif self.type_valeur == 'DATE':
            try:
                return datetime.strptime(self.valeur, '%Y-%m-%d').date()
            except ValueError:
                return None
        elif self.type_valeur == 'DATETIME':
            try:
                return datetime.fromisoformat(self.valeur)
            except ValueError:
                return None
        else:
            return self.valeur
    
    @classmethod
    def get(cls, cle, default=None):
        """Get a configuration value"""
        try:
            config = cls.objects.get(cle=cle)
            return config.get_valeur_typee()
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set(cls, cle, valeur, utilisateur=None):
        """Set a configuration value"""
        config, created = cls.objects.get_or_create(cle=cle)
        config.valeur = str(valeur)
        config.updated_by = utilisateur
        config.save()
        return config


# Predefined configurations to create
CONFIGURATIONS_PREDEFINIS = [
    {
        'cle': 'SYSTEME_NOM',
        'valeur': 'SI DITAS',
        'type_valeur': 'STRING',
        'categorie': 'SYSTEME',
        'description': 'System name',
        'modifiable': False,
    },
    {
        'cle': 'SYSTEME_VERSION',
        'valeur': '1.0.0',
        'type_valeur': 'STRING',
        'categorie': 'SYSTEME',
        'description': 'System version',
        'modifiable': False,
    },
    {
        'cle': 'SESSION_TIMEOUT',
        'valeur': '3600',
        'type_valeur': 'INTEGER',
        'categorie': 'SECURITE',
        'description': 'Session duration in seconds (1h)',
        'modifiable': True,
    },
    {
        'cle': 'DOUBLE_AUTH_OBLIGATOIRE',
        'valeur': 'false',
        'type_valeur': 'BOOLEAN',
        'categorie': 'SECURITE',
        'description': 'Mandatory two-factor authentication for all',
        'modifiable': True,
    },
    {
        'cle': 'MAX_TENTATIVES_CONNEXION',
        'valeur': '3',
        'type_valeur': 'INTEGER',
        'categorie': 'SECURITE',
        'description': 'Maximum login attempts',
        'modifiable': True,
    },
    {
        'cle': 'PAGINATION_DEFAUT',
        'valeur': '50',
        'type_valeur': 'INTEGER',
        'categorie': 'INTERFACE',
        'description': 'Number of items per page',
        'modifiable': True,
    },
    {
        'cle': 'RETENTION_AUDIT_JOURS',
        'valeur': '730',
        'type_valeur': 'INTEGER',
        'categorie': 'SYSTEME',
        'description': 'Audit logs retention period (2 years)',
        'modifiable': True,
    },
]
