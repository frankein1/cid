# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# core/templatetags/capacites.py
from django import template

register = template.Library()

@register.filter(name='peut')  # ✅ Nom plus court et clair
def peut(user, capacite):
    """
    Filtre de template pour vérifier les capacités utilisateur.
    Usage dans un template : {% if user|peut:"creer_dossier" %}
    
    Args:
        user: L'utilisateur à vérifier
        capacite: Le code de la capacité (ex: "peut_creer_dossier")
    
    Returns:
        bool: True si l'utilisateur a la capacité, False sinon
    """
    if not user or not user.is_authenticated:
        return False
    
    return user.a_la_capacite(capacite)

# ✅ Garder l'ancien nom pour compatibilité temporaire
@register.filter(name='a_la_capacite')
def a_la_capacite(user, capacite):
    """DEPRECATED: Utilisez 'peut' à la place"""
    return peut(user, capacite)
