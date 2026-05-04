# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# core/models/audit.py

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.conf import settings

class AuditLog(models.Model):
    """
    Audit log for complete traceability
    """
  
    ACTIONS = [
        ('CREATE', 'Creation'),
        ('READ', 'Consultation'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Deletion'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('EXPORT', 'Data export'),
        ('PRINT', 'Print'),
        ('VALIDATE', 'Validation'),
        ('REJECT', 'Rejection'),
        ('SEND', 'Send'),
        ('RECEIVE', 'Receive'),
    ]
    
    NIVEAUX = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    # Action
    action = models.CharField(max_length=20, choices=ACTIONS)
    
    niveau = models.CharField(max_length=20, choices=NIVEAUX, default='INFO')
    
    # User
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='actions_effectuees',
    )
    
    # Service at the time of action
    service = models.ForeignKey(
        'core.Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    
    # Concerned object (Generic Foreign Key)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    objet_concerne = GenericForeignKey('content_type', 'object_id')
    
    # Description
    description = models.TextField()
    
    # Technical details
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Before/after data, metadata"
    )
    
    # Technical context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    user_agent = models.TextField(blank=True)
    
    url = models.CharField(max_length=500, blank=True)
    
    methode_http = models.CharField(max_length=10, blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Execution duration (in milliseconds)
    duree_execution = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['utilisateur', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.utilisateur} - {self.get_action_display()}"
    
    @classmethod
    def log_action(cls, utilisateur, action, description, objet=None, service=None, 
                   request=None, details=None):
        """Utility method to create a log"""
        log = cls(
            utilisateur=utilisateur,
            action=action,
            description=description,
            service=service or (utilisateur.service_principal if utilisateur else None),
            details=details or {}
        )
        
        if objet:
            log.content_type = ContentType.objects.get_for_model(objet)
            log.object_id = objet.pk
        
        if request:
            log.ip_address = cls._get_client_ip(request)
            log.user_agent = request.META.get('HTTP_USER_AGENT', '')
            log.url = request.path
            log.methode_http = request.method
        
        log.save()
        return log
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
