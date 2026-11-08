# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/expulsion_apercu.py
"""Aperçu en administration des formulaires de la prévention des expulsions, sur des données fictives."""
from datetime import date

from logement.models import FormulaireOfficiel as F

FICTIF = {'date_retour': "20/11/2026", 'locataire': "EXEMPLE Lucie", 'adresse': "1 rue de l'Exemple, 13000 Exemple",
          'loyer': "650", 'charges': "50", 'numero_caf': "0000000", 'audience': "28/11/2026", 'nom': "EXEMPLE",
          'prenom': "Lucie", 'exploc': "EXPLOC-0000", 'caf': "0000000", 'convocations': "05/11/2026, 19/11/2026",
          'ts_nom': "AGENT", 'ts_prenom': "Exemple", 'organisme': "MDS Exemple – 1 rue de l'Exemple 13000 Exemple",
          'date': "08/11/2026", 'visa': "Visa C.E. le 08/11/2026"}


def apercu(formulaire):
    """(pdf, rapport) : le formulaire déposé, rempli avec des valeurs fictives."""
    from .expulsion_documents import placements_carence, placements_questionnaire
    from .pdf_officiel import remplir
    if formulaire.code == F.EXP_DSF:
        from .dsf import remplir_cerfa
        return remplir_cerfa({'Noms': "EXEMPLE", 'Prénoms': "Lucie", 'Date de naissance': "03/04/1990",
                              'Montant dette': "2400", 'Salaire_net_1': "1100", 'Loyer': "650",
                              'Evaluation sociale': "Évaluation fictive pour l'aperçu.", 'situation loca': "célibataire",
                              'Date 10': date(2026, 11, 28).strftime('%d/%m/%Y')}), {}
    champs = placements_carence() if formulaire.code == F.EXP_CARENCE else placements_questionnaire()
    return remplir(bytes(formulaire.contenu), champs, FICTIF, formulaire.reglages)
