# protection_enfance/informations_preoccupantes/integrations/parquet.py
class ServiceTransmissionParquet:
"""
Classe responsable d'orchestrer la transmission au Parquet.
L'implémentation réelle dépendra des canaux (email sécurisé, API, suivi).
"""


def transmettre_parquet(self, information_preoccupante, motif_urgence):
"""
Doit lever une exception si la transmission échoue.
Ex : envoyer email sécurisé / API selon procédure locale.
"""
payload = {
'numero': information_preoccupante.numero,
'nom_enfant': information_preoccupante.enfant_nom,
'date_creation': str(information_preoccupante.date_creation),
'motif': motif_urgence,
'description': information_preoccupante.description[:5000],
}
# TODO : implémenter l'envoi réel (SMTP sécurisé, API) selon procédure départementale
# Respecter confidentialité et preuve de transmission
return True
