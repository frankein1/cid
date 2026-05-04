# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/services/ip_manager.py
from django.utils import timezone
from django.db import transaction
from protection_enfance.models.informations_preoccupantes import InformationPreoccupante, HistoriqueAction
from protection_enfance.informations_preoccupantes.integrations.parquet import ServiceTransmissionParquet

class IPManager:
@staticmethod
def creer_information(data, auteur=None):
"""
data: dict contenant enfant_nom, description, origine, ...
Retourne l'instance InformationPreoccupante
"""
with transaction.atomic():
ip = InformationPreoccupante.create_with_numero(
auteur=auteur,
enfant_nom=data.get('enfant_nom'),
enfant_date_naissance=data.get('enfant_date_naissance'),
origine=data.get('origine','AUTRE'),
description=data.get('description',''),
)
HistoriqueAction.objects.create(
information=ip,
action="Création IP",
user=auteur,
commentaire=f"Créé par {auteur}" if auteur else "Création externe"
)
return ip

@staticmethod
def transmettre_au_parquet(information, motif, user=None):
"""
Ordonne la transmission au Parquet via le service d'intégration.
Ne change le statut que si la transmission est confirmée.
"""
svc = ServiceTransmissionParquet()
svc.transmettre_parquet(information_preoccupante=information, motif_urgence=motif)
information.transmit_parquet = True
information.transmis_parquet_date = timezone.now()
information.statut = 'TRANSMIS_PARQUET'
information.save()
HistoriqueAction.objects.create(
information=information,
action="Transmission au Parquet",
user=user,
commentaire=f"Motif: {motif}"
)
return information


@staticmethod
def ajouter_action(information, action, user=None, commentaire=''):
HistoriqueAction.objects.create(
information=information,
action=action,
user=user,
commentaire=commentaire
)
