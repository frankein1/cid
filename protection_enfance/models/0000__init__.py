# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/models/__init__.py - CORRIGÉ
# from .informations_preoccupantes.signalements import SignalementCRIP  # ⚠️ N'EXISTE PAS
from .informations_preoccupantes import InformationPreoccupante, HistoriqueAction, NumeroCounter
# from .informations_preoccupantes.evaluations import EnqueteSociale    # ⚠️ N'EXISTE PAS  
# from .informations_preoccupantes.decisions import DecisionProtection  # ⚠️ N'EXISTE PAS

# from .placements.base import Placement                                # ⚠️ N'EXISTE PAS
# from .placements.familles_accueil import FamilleAccueil, PlacementFamilleAccueil  # ⚠️ N'EXISTE PAS
# from .placements.mef import MEF, PlacementMEF                        # ⚠️ N'EXISTE PAS
# from .placements.domicile import PlacementDomicile                   # ⚠️ N'EXISTE PAS
# from .placements.tiers_confiance import PlacementTiersConfiance      # ⚠️ N'EXISTE PAS

# from .adoption import ProcedureAdoption, AgrementAdoption            # ⚠️ N'EXISTE PAS
# from .mesures_educatives import MesureEducative                      # ⚠️ N'EXISTE PAS

# from .referentiels.crip import CRIP                                  # ⚠️ N'EXISTE PAS
# from .referentiels.criteres_danger import CriteresDanger             # ⚠️ N'EXISTE PAS  
# from .referentiels.mesures_protection import MesureProtection        # ⚠️ N'EXISTE PAS

__all__ = [
    # 'SignalementCRIP', 
    'InformationPreoccupante',
    'HistoriqueAction',
    'NumeroCounter'
    # 'EnqueteSociale', 
    # 'DecisionProtection',
    # 'Placement', 
    # 'FamilleAccueil', 
    # 'PlacementFamilleAccueil',
    # 'MEF', 'PlacementMEF',
    # 'PlacementDomicile', 
    # 'PlacementTiersConfiance', 
    # 'ProcedureAdoption', 
    # 'AgrementAdoption',
    # 'MesureEducative', 
    # 'CRIP', 
    # 'CriteresDanger', 
    # 'MesureProtection'
]
