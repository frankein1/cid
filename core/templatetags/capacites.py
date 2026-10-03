# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
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


@register.simple_tag
def peut_agir(user, obj, action):
    """
    Capacité métier + barrière territoriale (MDS) sur un objet.
    Usage : {% peut_agir user objet 'peut_modifier' as ok %}
    """
    if not user or not user.is_authenticated:
        return False
    return user.peut_agir_sur_objet(obj, action)
