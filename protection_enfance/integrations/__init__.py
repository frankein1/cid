# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/integrations/__init__.py
from .parquet import ServiceTransmissionParquet
from .calendriers import ServiceCalendrierCRIP

__all__ = ['ServiceTransmissionParquet', 'ServiceCalendrierCRIP']
