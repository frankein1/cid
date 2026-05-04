# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# core/authentication/backends.py - COMPLÉTÉ

"""
Backend d'authentification local pour le Conseil Départemental 13
CORRIGÉ COMPLET : Import différé pour éviter circularité
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)


class CD13LocalBackend(ModelBackend):
    """
    Backend d'authentification local pour le Conseil Départemental 13
    CORRIGÉ : Import différé d'AuditLog pour éviter circularité
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Appeler le parent d'abord
        user = super().authenticate(request, username, password, **kwargs)
        
        if user is not None and request is not None:
            # Logger la connexion réussie (import différé)
            try:
                from core.models.audit import AuditLog  # IMPORT DIFFÉRÉ
                
                ip_address = self._get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
                
                AuditLog.objects.create(
                    utilisateur=user,
                    action='LOGIN_SUCCESS',
                    description=f"Connexion locale réussie: {username}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    url=request.path,
                    methode_http=request.method,
                    duree_execution=0,
                )
                
                # Mettre à jour les statistiques
                user.derniere_connexion_ip = ip_address
                user.nombre_connexions = (user.nombre_connexions or 0) + 1
                
                # Sauvegarder sans déclencher de signaux inutiles
                User = get_user_model()
                User.objects.filter(pk=user.pk).update(
                    derniere_connexion_ip=user.derniere_connexion_ip,
                    nombre_connexions=user.nombre_connexions
                )
                
            except Exception as e:
                # Ne pas bloquer l'authentification
                logger.error(f"Erreur lors du logging d'authentification: {e}")
        
        elif user is None and request is not None:
            # Logger les tentatives d'authentification échouées
            try:
                from core.models.audit import AuditLog  # IMPORT DIFFÉRÉ
                
                ip_address = self._get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
                
                AuditLog.objects.create(
                    utilisateur=None,
                    action='LOGIN_FAILED',
                    description=f"Échec connexion: {username}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    url=request.path,
                    methode_http=request.method,
                    duree_execution=0,
                )
            except Exception:
                pass  # Ignorer les erreurs de logging
        
        return user
    
    def get_user(self, user_id):
        """Récupère un utilisateur par son ID"""
        try:
            User = get_user_model()
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def _get_client_ip(request):
        """Récupère l'adresse IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
