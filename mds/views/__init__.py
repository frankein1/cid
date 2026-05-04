# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# mds/views/__init__.py

from .base_views import (
    liste_mds, detail_mds, creer_mds, modifier_mds, statistiques_mds
)
from .user_views import (
    gestion_utilisateurs_mds, ajouter_utilisateur_mds, 
    modifier_profil_utilisateur, supprimer_utilisateur_mds
)
from .reception_views import (
    mes_demi_journees, toggle_demi_journee
)
from .api_views import (
    ajax_get_ville_from_cp, get_utilisateurs_mds_json, get_salles_mds_json
)
from .salle_views import (
    gestion_salles_mds, creer_salle_mds, 
    modifier_salle_mds, supprimer_salle_mds
)
