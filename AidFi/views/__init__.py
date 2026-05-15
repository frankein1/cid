# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/views/__init__.py - UNIFIE TOUTES LES VUES

from .v_afase import (
    afase_creer_ou_modifier,
    afase_detail,
    afase_evaluation,
    afase_decision,
    afase_previsualisation,
    ajouter_document_afase,
    afase_pdf,
)

# Alias pour compatibilité (si tu ne l'as pas mis dans v_afase.py)
# afase_creer = afase_creer_ou_modifier  # ← à décommenter si besoin

from .v_regie import (
    regie_urgence_create,
    regie_detail,
)

from .v_cap import (
    cap_attribution,
    cap_detail,
)

from .v_cadre import (
    dashboard_cadre,
)
