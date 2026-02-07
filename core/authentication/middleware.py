# core/authentication/middleware.py - VERSION CORRIGÉE

import time
from django.utils.deprecation import MiddlewareMixin

class AuditMiddleware(MiddlewareMixin):
    """
    Middleware pour tracer automatiquement les requêtes
    CORRIGÉ : Import différé d'AuditLog + filtrage optimisé
    """
    
    def process_request(self, request):
        request._audit_start_time = time.time()
    
    def process_response(self, request, response):
        # ✅ VÉRIFIER D'ABORD SI ON DOIT AUDITER
        if self._should_audit(request, response):
            # ✅ IMPORT DIFFÉRÉ pour éviter le RuntimeWarning
            from core.models import AuditLog
            
            duree = int((time.time() - request._audit_start_time) * 1000)
            
            AuditLog.objects.create(
                utilisateur=request.user if request.user.is_authenticated else None,
                action=self._get_action(request),
                description=f"{request.method} {request.path}",
                ip_address=AuditLog._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                url=request.path,
                methode_http=request.method,
                duree_execution=duree,
            )
        
        return response
    
    def _should_audit(self, request, response):
        """Détermine si la requête doit être tracée"""
        # ✅ EXCLUSIONS EN PREMIER (plus performant)
        # Ne pas tracer les ressources statiques
        if request.path.startswith(('/static/', '/media/')):
            return False
        
        # ✅ NOUVELLES EXCLUSIONS POUR ÉVITER LE SPAM
        if '/api/heartbeat/' in request.path:
            return False
        if request.path.startswith('/ajax/'):
            return False
        
        # Tracer uniquement les actions de modification
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return True
        
        # Tracer les exports et impressions
        if 'export' in request.path or 'print' in request.path:
            return True
        
        return False
    
    def _get_action(self, request):
        """Détermine le type d'action"""
        method_map = {
            'POST': 'CREATE',
            'PUT': 'UPDATE',
            'PATCH': 'UPDATE',
            'DELETE': 'DELETE',
            'GET': 'READ',
        }
        
        if 'export' in request.path:
            return 'EXPORT'
        if 'print' in request.path:
            return 'PRINT'
        
        return method_map.get(request.method, 'READ')


class ServiceSelectorMiddleware(MiddlewareMixin):
    """
    Middleware pour gérer la sélection du service actif
    CORRIGÉ : Import différé de Service
    """
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Récupérer le service actif depuis la session
            service_id = request.session.get('service_actif_id')
            
            if service_id:
                try:
                    # ✅ IMPORT DIFFÉRÉ pour éviter le RuntimeWarning
                    from core.models import Service
                    request.service_actif = Service.objects.get(id=service_id)
                except Service.DoesNotExist:
                    # Fallback sur service principal si disponible
                    request.service_actif = getattr(request.user, 'service_principal', None)
            else:
                # Par défaut: service principal
                request.service_actif = getattr(request.user, 'service_principal', None)
                if request.service_actif:
                    request.session['service_actif_id'] = request.service_actif.id
