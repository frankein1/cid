# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/templatetags/budget_afase.py
from django import template

register = template.Library()


@register.simple_tag
def valeur_budget(grille, prefixe, code, colonne):
    """Valeur d'une case du budget : grille[f"{prefixe}__{code}__{colonne}"] (vide si 0)."""
    v = (grille or {}).get(f"{prefixe}__{code}__{colonne}", "")
    try:
        return "" if colonne != 'precision' and float(v or 0) == 0 else v
    except (TypeError, ValueError):
        return v
