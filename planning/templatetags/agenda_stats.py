# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/templatetags/agenda_stats.py
from django import template

from planning.statistiques import heures as _heures

register = template.Library()


@register.filter
def heures(minutes):
    """Minutes → « 3h30 » (ou « – » si zéro)."""
    return _heures(minutes)
