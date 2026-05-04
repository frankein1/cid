# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# core/templatetags/permissions_tags.py

from django import template

register = template.Library()

@register.filter
def peut_modifier_objet(user, objet):
    """Vérifie si l'utilisateur peut modifier l'objet"""
    return user.peut_agir_sur_objet(objet, "peut_modifier")
