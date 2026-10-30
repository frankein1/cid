# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/models/__init__.py - UNIFIE TOUS LES MODÈLES
# LEGACY (migrations uniquement)
from .legacy import aide_piece_upload_path, validate_file_size
from .legacy_models import aide_piece_upload_path as legacy_upload_path  # Migration 0005

# MODÈLES MODULAIRES
from .m_generique import (
    TypeAide, MotifDemande, DemandeAide, SuiviDemande, PieceJustificative
)
from .m_regie import DemandeRegie
from .m_referentiel import ParametresAides, ReferentielMotifAFASE, MontantIndicatifAFASE, MotifRefusAFASE
from .m_recours import RecoursAFASE
from .m_cap import ReceptionCAP, TitreCAP, DemandeCAP, InventaireCAP
from .m_afase import (
    DemandeAFASE, EvaluationSocialeAFASE, BudgetAFASE, DecisionAFASE, EnfantAFASE
)

__all__ = [
    'TypeAide', 'DemandeAide', 'DemandeRegie', 'DemandeAFASE', 'DemandeCAP', 'RecoursAFASE'
]
