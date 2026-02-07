# core/views/ajax.py
"""
Vues AJAX génériques pour l'application CORE
Ces endpoints sont réutilisables par toutes les apps (mds, beneficiaire, etc.)
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

# Import des utilitaires code postal
try:
    from core.utils.cp import get_ville_from_cp, get_villes_multiples
except ImportError:
    # Fallback si le module n'existe pas encore
    def get_ville_from_cp(code_postal):
        return ""
    def get_villes_multiples(code_postal):
        return []


@login_required
@require_http_methods(["GET"])
def ajax_ville_par_cp(request):
    """
    Endpoint AJAX pour récupérer la ville à partir d'un code postal
    
    URL: /ajax/ville-par-cp/?cp=13001
    Méthode: GET
    Retour JSON: {"success": true, "ville": "Marseille 1er", "villes": ["Marseille 1er"]}
    
    Utilisé par:
    - Formulaire MDS (création/modification)
    - Formulaire Bénéficiaire (création/modification)
    - Tous les formulaires nécessitant code postal -> ville
    
    Returns:
        JsonResponse: Toujours avec les clés 'success', 'ville', 'villes'
                     pour éviter les erreurs "undefined" en JavaScript
    """
    code_postal = request.GET.get('cp', '').strip()
    
    # Validation : code postal manquant
    if not code_postal:
        return JsonResponse({
            'success': False,
            'error': 'Code postal manquant',
            'ville': '',
            'villes': []
        }, status=400)
    
    # Validation : format incorrect
    if len(code_postal) != 5 or not code_postal.isdigit():
        return JsonResponse({
            'success': False,
            'error': 'Format de code postal invalide (5 chiffres requis)',
            'ville': '',
            'villes': []
        }, status=400)
    
    # Récupération de la ville via l'utilitaire
    ville = get_ville_from_cp(code_postal)
    villes = get_villes_multiples(code_postal)
    
    # Protection contre None (l'API peut retourner None)
    ville = ville or ''
    villes = villes or []
    
    # Code postal non trouvé
    if not ville and not villes:
        return JsonResponse({
            'success': False,
            'error': 'Code postal non trouvé',
            'code_postal': code_postal,
            'ville': '',
            'villes': []
        }, status=404)
    
    # Succès
    return JsonResponse({
        'success': True,
        'ville': ville or (villes[0] if villes else ''),
        'villes': villes if villes else ([ville] if ville else []),
        'code_postal': code_postal
    })


# ============================================================================
# Ajoutez ici d'autres endpoints AJAX génériques si nécessaire
# ============================================================================
