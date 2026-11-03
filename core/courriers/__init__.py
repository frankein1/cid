# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/courriers/__init__.py
"""
Modèles de courriers : textes modifiables en administration (registre.py), rendus en paragraphes (rendu.py).

Usage dans un service PDF :
    from core.courriers import modele_texte, rendu
    m = modele_texte("AFASE_ACCORD")
    objet = rendu.ligne(m["objet"], valeurs, conditions)
    paragraphes = rendu.paragraphes(m["corps"], valeurs, conditions)
"""
from core.courriers import rendu  # noqa: F401


def modele_texte(code):
    """Textes en vigueur d'un courrier : ceux de l'administration s'ils existent, sinon ceux du registre."""
    from core.courriers.registre import COURRIERS, CHAMPS
    from core.models import ModeleCourrier
    d = COURRIERS[code]
    m = ModeleCourrier.objects.filter(code=code).first()
    if m:
        return {c: getattr(m, c) for c in CHAMPS}
    return {c: d.get(c, "") for c in CHAMPS}
