# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# ged/ged_tags.py

from django import template
from django.contrib.contenttypes.models import ContentType

register = template.Library()

# =========================
# GED
# =========================

@register.inclusion_tag('ged/alerte_badge.html', name='alerte_documents')
def check_ged_alerts(beneficiaire):
    """
    Badge d’alerte GED pour un bénéficiaire.
    """
    from ged.models import DocumentGED

    if not beneficiaire:
        return {'count': 0}

    obj_type = ContentType.objects.get_for_model(beneficiaire)

    count = DocumentGED.objects.filter(
        content_type=obj_type,
        object_id=beneficiaire.id,
        statut='VALIDE',
        notification_envoyee=True,
        alerte_active=True,
    ).count()

    return {'count': count}


@register.filter
def peut_modifier_ged(document, user):
    """
    Règle GED UNIQUE :
    délègue au modèle DocumentGED.
    """
    if not user or not user.is_authenticated:
        return False

    return document.peut_etre_modifie_par(user)


# =========================
# CORE (DÉLÉGATION PURE)
# =========================

@register.filter(name='a_la_capacite')
def a_la_capacite(user, capacite_nom):
    """
    Délégation directe au CORE.
    """
    if not user or not user.is_authenticated:
        return False
    return user.a_la_capacite(capacite_nom)


@register.simple_tag
def peut_agir(user, obj, action):
    if not user or not user.is_authenticated:
        return False
    return user.peut_agir_sur_objet(obj, action)
