# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/apercu.py
"""Demande fictive pour l'aperçu d'un formulaire officiel en administration (aucune donnée réelle)."""
import datetime
import types


def demande_fictive():
    dn = {
        'num_caf': '0000000', 'bailleur_type': 'PRIVE', 'adresse_objet': '1 rue de l\'Exemple, appartement 2',
        'cp_commune': '13000 Ville-Exemple', 'nouveau_bailleur': 'Bailleur Exemple\n2 avenue Fictive 13000 Ville-Exemple',
        'contact_bailleur': '04 00 00 00 00', 'situation_familiale': 'MARITALE',
        'composition': [
            {'role': 'DEMANDEUR', 'nom': 'EXEMPLE', 'prenom': 'Alex', 'date_naissance': '01/01/1990',
             'nationalite': 'Fictive', 'situation': 'En activité'},
            {'role': 'CONJOINT', 'nom': 'EXEMPLE', 'prenom': 'Sam', 'date_naissance': '01/01/1991',
             'nationalite': 'Fictive', 'situation': 'Sans emploi'},
            {'role': 'ENFANT', 'nom': 'EXEMPLE', 'prenom': 'Noa', 'date_naissance': '01/01/2016', 'situation': 'Scolarisé'}],
        'ressources': {'salaires': {'demandeur': '1000'}, 'france_travail': {'conjoint': '500'},
                       'prestations_familiales': {'demandeur': '100'}, 'autres_1': {'autres': '10'}},
        'ressources_precisions': {'prestations_familiales': 'AF', 'autres_1': 'exemple'}, 'quotient_familial': '500',
        'logement_anterieur': {'bailleur': 'Hébergement (exemple)', 'nature': 'Hébergé', 'typologie': 'T1',
                               'statut': 'Hébergé', 'motif': 'Trop petit', 'caution_restituee': 'NON'},
        'logement_nouveau': {'bailleur': 'Bailleur Exemple', 'typologie': 'T3', 'classe_energetique': 'C', 'loyer': '600',
                             'charges': '50', 'chauffage_collectif': 'NON', 'montant_caution': '600',
                             'al_previsionnel': '250', 'loyer_residuel': '400', 'date_entree': '01/01/2027',
                             'demande_al_le': '15/12/2026'},
        'garantie': '4_12', 'proposition': {'caution': '600', 'premier_loyer': '650', 'equipements': '180'},
        'equipements': ['refrigerateur'],
        'ts': {'nom': 'EXEMPLE', 'prenom': 'Dominique', 'qualite': 'Assistant de service social',
               'telephone': '04 00 00 00 01', 'email': 'mds@exemple.fr', 'organisme': 'MDS Exemple – 1 place Fictive'},
    }
    return types.SimpleNamespace(
        donnees=dn, avis='FAVORABLE', avis_motive="Avis fictif pour vérifier la mise en page.",
        proposition_pret=200, proposition_subvention=1230, pieces={'formulaire': 'FOURNIE', 'bail': 'MANQUANTE'},
        note_cadre="Note fictive.", date_validation_cadre=datetime.datetime(2026, 1, 1), cadre=None, mds=None,
        beneficiaire=None)
