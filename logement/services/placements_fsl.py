# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/placements_fsl.py
"""Placement des données sur les formulaires officiels du FSL (aide à l'accès), version 03/2025.

Les ancres sont de courts libellés imprimés sur les formulaires vierges (« Loyer : », « Nom du travailleur social »),
pas leur contenu : les PDF eux-mêmes ne sont jamais dans le dépôt, ils sont déposés en administration.
Un champ mal placé se corrige sans toucher au code : « Réglages » du formulaire en administration."""
from .fsl import COLONNES, EQUIPEMENTS, PROPOSITION, RESSOURCES_FSL, d, montant, taux_effort, totaux_ressources

G = 300           # sépare les colonnes gauche / droite des pages 2 (logement antérieur / objet de la demande)
D = 600           # moitié droite de la page A3

LIGNES_COMPOSITION = [('Demandeur', 0), ('Conjoint', 0), ('Enfant 1', 0), ('Enfant 2', 0), ('Enfant 3', 0),
                      ('Enfant 4', 0), ('Enfant 5', 0), ('Autres personnes', 0), ('Autres personnes', 1)]
COLONNES_COMPOSITION = [('nom', 'Nom', 4), ('prenom', 'Prénom', -8), ('date_naissance', 'Date de naissance', 0),
                        ('nationalite', 'Nationalité', -4), ('situation', 'Situation actuelle', -10)]
ANCRES_RESSOURCES = {
    'salaires': ('Salaires', 0), 'france_travail': ('Allocations France Travail', 0), 'rsa': ('RSA', 0),
    'prime_activite': ("Prime d'activité", 0), 'ij': ('Indemnités journalières', 0),
    'pension': ('Pension (préciser)', 0), 'pension_complementaire': ('Pension complémentaire', 0),
    'prestations_familiales': ('Prestations familiales', 0), 'autres_1': ('Autres ressources', 0),
    'autres_2': ('Autres ressources', 15), 'autres_3': ('Autres ressources', 30),
}
ANCRES_PROPOSITION = {'caution': 'Caution :', 'caution_differentielle': 'Caution différentielle',
                      'premier_loyer': 'mois de loyer chargé', 'compteurs': "Frais d'ouverture des compteurs",
                      'assurance': 'Assurance :', 'equipements': 'Equipements de première nécessité'}
ANCRES_EQUIPEMENTS = {'table_cuisson': 'Table de cuisson', 'refrigerateur': 'Réfrigérateur',
                      'lave_linge': 'Lave-linge', 'lit_140': 'Lit 140', 'lit_90': 'Lit 90',
                      'table_chaises': 'Table et chaise'}


def _formulaire_acces():
    c = [
        {'cle': 'bailleur_social', 'page': 0, 'ancre': 'BAILLEUR SOCIAL', 'mode': 'case', 'dx': -2},
        {'cle': 'bailleur_prive', 'page': 0, 'ancre': 'BAILLEUR PRIVE', 'mode': 'case', 'dx': -2},
        {'cle': 'num_caf', 'page': 0, 'ancre': 'Allocataire CAF 13', 'dx': 12},
        {'cle': 'autres_numero', 'page': 0, 'ancre': 'Autres :', 'dx': 4},
        {'cle': 'demandeur', 'page': 0, 'ancre': 'Nom(s) et Prénom du demandeur', 'mode': 'dessous', 'dy': 2},
        {'cle': 'adresse_objet', 'page': 0, 'ancre': 'Adresse objet de la demande', 'mode': 'dessous', 'dy': 2,
         'largeur': 480, 'lignes': 2, 'interligne': 22},
        {'cle': 'cp_commune', 'page': 0, 'ancre': 'Code Postal et Commune', 'dx': 8},
        {'cle': 'nouveau_bailleur', 'page': 0, 'ancre': 'NOM et ADRESSE du nouveau bailleur', 'mode': 'dessous',
         'dy': 2, 'largeur': 480, 'lignes': 2, 'interligne': 22},
        {'cle': 'contact_bailleur', 'page': 0, 'ancre': 'Coordonnées téléphoniques et/ou adresse mail du bailleur',
         'dx': 40},
    ]
    for code, ancre in [('CELIBATAIRE', 'Célibataire'), ('SEPARE', 'Séparé(e)'), ('MARITALE', 'Vie maritale'),
                        ('DIVORCE', 'Divorcé(e)'), ('MARIE', 'Marié'), ('VEUF', 'Veuf(ve)')]:
        c.append({'cle': f'sf_{code}', 'page': 0, 'ancre': ancre, 'mode': 'case', 'dx': -6})
    for i, (ancre, occ) in enumerate(LIGNES_COMPOSITION):
        for col, entete, dx in COLONNES_COMPOSITION:
            c.append({'cle': f'comp_{i}_{col}', 'page': 0, 'ancre': ancre, 'occ': occ, 'x_min': D,
                      'mode': 'cellule', 'col': entete, 'dx': dx, 'taille': 8, 'dy': -2})
    # page 2 : ressources
    for code, (ancre, decal) in ANCRES_RESSOURCES.items():
        for col, entete in [('demandeur', 'Demandeur'), ('conjoint', 'Conjoint'), ('autres', 'Autres personnes au foyer')]:
            c.append({'cle': f'res_{code}_{col}', 'page': 1, 'ancre': ancre, 'x_max': 120, 'mode': 'cellule',
                      'col': entete, 'col_x_max': D, 'dx': -12, 'dy': decal})
    # précisions (« Pension (préciser) », « Prestations familiales (préciser) », autres ressources)
    c += [{'cle': 'prec_pension', 'page': 1, 'ancre': 'Pension (préciser)', 'x_max': 120, 'dx': 0, 'taille': 6},
          {'cle': 'prec_prestations_familiales', 'page': 1, 'ancre': '(préciser)', 'occ': 1, 'x_max': 120, 'dx': 0,
           'taille': 6},
          {'cle': 'prec_autres_1', 'page': 1, 'ancre': 'Autres ressources', 'x_max': 120, 'mode': 'abs', 'dy': 7,
           'taille': 6}]
    for code, decal in (('autres_2', 15), ('autres_3', 30)):
        c.append({'cle': f'prec_{code}', 'page': 1, 'ancre': 'Autres ressources', 'x_max': 120, 'mode': 'abs',
                  'dy': decal - 1, 'taille': 7})
    for col, entete in [('demandeur', 'Demandeur'), ('conjoint', 'Conjoint'), ('autres', 'Autres personnes au foyer')]:
        c.append({'cle': f'total_{col}', 'page': 1, 'ancre': 'TOTAL', 'x_max': 120, 'mode': 'cellule', 'col': entete,
                  'col_x_max': D, 'dx': -12})
    c += [
        {'cle': 'total_ressources', 'page': 1, 'ancre': 'Total ressources', 'dx': 80},
        {'cle': 'quotient_familial', 'page': 1, 'ancre': 'Quotient familial', 'dx': 20},
        {'cle': 'taux_effort', 'page': 1, 'ancre': "Taux d'effort", 'dx': 20},
    ]
    # logement antérieur (colonne gauche) et objet de la demande (colonne droite)
    ant = [('ant_bailleur', 'Nom ou raison social du bailleur', 'dessous', 0, 2), ('ant_nature', 'Nature', 'apres', 18, 0),
           ('ant_typologie', 'Typologie du logement', 'apres', 6, 0), ('ant_statut', "Statut d'occupation", 'apres', 18, 0),
           ('ant_loyer', 'Loyer :', 'apres', 4, 0), ('ant_charges', 'Charges locatives :', 'apres', 4, 0),
           ('ant_al', 'Montant A.L ou A.P.L :', 'apres', 4, 0), ('ant_loyer_residuel', 'Loyer résiduel', 'apres', 8, 0),
           ('ant_motif', 'Motif de la demande de relogement', 'apres', 22, 0)]
    for cle, ancre, mode, dx, dy in ant:
        c.append({'cle': cle, 'page': 1, 'ancre': ancre, 'x_max': G, 'mode': mode, 'dx': dx, 'dy': dy, 'taille': 8})
    c += [{'cle': 'ant_caution_oui', 'page': 1, 'ancre': 'OUI', 'x_max': G, 'dx': 1},
          {'cle': 'ant_caution_non', 'page': 1, 'ancre': 'NON', 'x_max': G, 'dx': 1}]
    nv = [('nv_bailleur', 'Nom ou raison social du bailleur', 'dessous', 0, 2), ('nv_typologie', 'Typologie du logement', 'apres', 6, 0),
          ('nv_classe_energetique', 'Classe énergétique', 'apres', 8, 0), ('nv_loyer', 'Loyer :', 'apres', 2, 0),
          ('nv_charges', 'Charges locatives :', 'apres', 2, 0), ('nv_montant_caution', 'Montant caution', 'apres', 8, 0),
          ('nv_al_previsionnel', 'Montant A.L ou A.P.L prévisionnel', 'apres', 8, 0),
          ('nv_loyer_residuel', 'Loyer résiduel', 'apres', 8, 0), ('nv_date_entree', "Date d'entrée dans les lieux", 'apres', 8, 0),
          ('nv_demande_al_le', "Demande d'A.L/ A.P.L déposée le", 'apres', 8, 0)]
    for cle, ancre, mode, dx, dy in nv:
        c.append({'cle': cle, 'page': 1, 'ancre': ancre, 'x_min': G, 'x_max': D, 'mode': mode, 'dx': dx, 'dy': dy, 'taille': 8})
    c += [{'cle': 'nv_chauffage_oui', 'page': 1, 'ancre': 'OUI', 'x_min': G, 'x_max': D, 'dx': 1},
          {'cle': 'nv_chauffage_non', 'page': 1, 'ancre': 'NON', 'x_min': G, 'x_max': D, 'dx': 1}]
    # proposition du travailleur social
    c += [{'cle': 'garantie_4_12', 'page': 1, 'ancre': '4/12', 'mode': 'case', 'dx': 0},
          {'cle': 'garantie_12_36', 'page': 1, 'ancre': '12/36', 'mode': 'case', 'dx': 0}]
    for code, ancre in ANCRES_PROPOSITION.items():
        c.append({'cle': f'prop_{code}', 'page': 1, 'ancre': ancre, 'x_min': D, 'mode': 'cellule', 'col': 'Proposition TS',
                  'dx': 0})
        c.append({'cle': f'case_{code}', 'page': 1, 'ancre': ancre, 'x_min': D, 'mode': 'case',
                  'dx': -11 if code == 'premier_loyer' else 0})
    for code, ancre in ANCRES_EQUIPEMENTS.items():
        c.append({'cle': f'eq_{code}', 'page': 1, 'ancre': ancre, 'x_min': D, 'mode': 'case', 'dx': 0})
    c += [
        {'cle': 'ts_nom', 'page': 1, 'ancre': 'Nom du travailleur social', 'dx': 12},
        {'cle': 'ts_prenom', 'page': 1, 'ancre': 'Prénom :', 'x_min': D, 'top_min': 400, 'dx': 4},
        {'cle': 'ts_qualite', 'page': 1, 'ancre': 'Educateur spécialisé)', 'dx': 10},
        {'cle': 'ts_telephone', 'page': 1, 'ancre': 'ligne directe', 'dx': 10},
        {'cle': 'ts_portable', 'page': 1, 'ancre': 'téléphone portable', 'dx': 10},
        {'cle': 'ts_email', 'page': 1, 'ancre': 'Adresse mail TS', 'dx': 10},
        {'cle': 'ts_organisme', 'page': 1, 'ancre': "Nom et adresse de l'organisme", 'dx': 10, 'largeur': 330, 'lignes': 3},
    ]
    return c


def _composition_et_ressources():
    """Situation familiale, composition (page 1) et ressources (page 2) : identiques sur les formulaires FSL."""
    return [x for x in _formulaire_acces()
            if x['cle'].startswith(('sf_', 'comp_', 'res_', 'prec_', 'total_'))
            or x['cle'] in ('num_caf', 'autres_numero', 'demandeur', 'cp_commune', 'quotient_familial', 'taux_effort')]


ANCRES_SITUATION_LOGEMENT = {'LOCATAIRE': 'Locataire', 'PROPRIETAIRE': 'Propriétaire', 'ACCESSION': 'En accession',
                             'HEBERGEMENT_TEMPORAIRE': 'En hébergement temporaire',
                             'RESIDENCE_SOCIALE': 'En résidence sociale', 'HEBERGE_TIERS': 'Hébergé par un tiers'}


def _formulaire_fluides(eau):
    c = [dict(x, dx=-1) if x['cle'].startswith('sf_') else x for x in _composition_et_ressources()
         if x['cle'] != 'taux_effort']
    c += [{'cle': 'distributeur', 'page': 0, 'ancre': 'Nom du distributeur' if eau else "Nom fournisseur d'énergie",
           'dx': 6},
          {'cle': 'adresse', 'page': 0, 'ancre': 'Adresse :', 'x_min': D, 'mode': 'dessous', 'dy': 2, 'largeur': 480,
           'lignes': 2, 'interligne': 22},
          {'cle': 'montant_loyer', 'page': 0, 'ancre': 'mensualité du prêt', 'dx': 20}]
    for code, ancre in ANCRES_SITUATION_LOGEMENT.items():
        c.append({'cle': f'sl_{code}', 'page': 0, 'ancre': ancre, 'x_min': D, 'mode': 'case', 'dx': -6})
    c += [
        {'cle': 'ts_nom', 'page': 1, 'ancre': "Nom de l'agent instructeur", 'dx': 12},
        {'cle': 'ts_prenom', 'page': 1, 'ancre': 'Prénom :', 'x_min': D, 'top_max': 200, 'dx': 4},
        {'cle': 'ts_qualite', 'page': 1, 'ancre': 'agent administratif) :', 'dx': 6},
        {'cle': 'ts_telephone', 'page': 1, 'ancre': 'ligne directe', 'dx': 10},
        {'cle': 'ts_portable', 'page': 1, 'ancre': 'téléphone portable', 'dx': 10},
        {'cle': 'ts_email', 'page': 1, 'ancre': 'Adresse mail TS/agent administratif', 'dx': 10},
        {'cle': 'ts_organisme', 'page': 1, 'ancre': "Nom et adresse de l'organisme", 'mode': 'dessous', 'dy': 2,
         'largeur': 520, 'lignes': 3, 'interligne': 18},
        {'cle': 'charges_exceptionnelles', 'page': 1, 'ancre': 'Charges exceptionnelles avec justificatifs', 'dx': 92,
         'largeur': 330, 'taille': 8},
        {'cle': 'surendettement_oui', 'page': 1, 'ancre': 'Oui', 'ligne_de': 'Surendettement', 'mode': 'case'},
        {'cle': 'surendettement_non', 'page': 1, 'ancre': 'Non', 'ligne_de': 'Surendettement', 'mode': 'case'},
        {'cle': 'commentaire_administratif', 'page': 1, 'ancre': 'Commentaire (si besoin)', 'mode': 'dessous', 'dy': 2,
         'largeur': 330, 'lignes': 6, 'interligne': 14, 'taille': 8},
    ]
    if eau:
        c += [{'cle': 'date_facture', 'page': 1, 'ancre': 'Date de la facture sur relevé', 'dx': 10},
              {'cle': 'montant_facture', 'page': 1, 'ancre': 'Montant de la facture', 'dx': 10}]
    else:
        c += [{'cle': 'dette_electricite', 'page': 1, 'ancre': "Montant de la dette d'électricité", 'dx': 10},
              {'cle': 'dette_gaz', 'page': 1, 'ancre': 'Montant de la dette de gaz', 'dx': 10},
              {'cle': 'participation_oui', 'page': 1, 'ancre': 'Oui', 'ligne_de': 'ticipation du ménage', 'mode': 'case'},
              {'cle': 'participation_non', 'page': 1, 'ancre': 'Non', 'ligne_de': 'ticipation du ménage', 'mode': 'case'},
              {'cle': 'plan_fournisseur', 'page': 1, 'ancre': 'ciser la proposition de plan de financement', 'dx': -12,
               'mode': 'dessous', 'dy': 0, 'largeur': 520, 'lignes': 3, 'interligne': 13, 'taille': 8}]
    return c


def _formulaire_maintien():
    """Page 1 (droite) : partie bailleur ; page 2 : situation familiale, composition et ressources à gauche,
    concordat / maintien et travailleur social à droite."""
    c = []
    for x in _composition_et_ressources():
        cle = x['cle']
        if cle.startswith(('sf_', 'comp_', 'res_', 'prec_', 'total_')) or cle in ('quotient_familial', 'taux_effort'):
            x = dict(x, page=1)
            if cle.startswith('comp_'):
                x.pop('x_min', None)
                x['x_max'] = 590
            if cle.startswith('sf_'):
                x['dx'] = -1
            if x.get('ancre') == 'Allocations France Travail':
                x['ancre'] = 'Alloc France Travail'
            if x.get('ancre') == 'Pension (préciser)':
                x['ancre'] = 'Pension'
                if cle == 'prec_pension':
                    x['dx'] = 36
            c.append(x)
    c += [
        {'cle': 'bailleur_social', 'page': 0, 'ancre': 'BAILLEUR SOCIAL', 'mode': 'case', 'dx': -2},
        {'cle': 'bailleur_prive', 'page': 0, 'ancre': 'BAILLEUR PRIVE', 'mode': 'case', 'dx': -2},
        {'cle': 'num_caf', 'page': 0, 'ancre': 'Allocataire CAF 13', 'dx': 12},
        {'cle': 'autres_numero', 'page': 0, 'ancre': 'Autres :', 'dx': 4},
        {'cle': 'demandeur', 'page': 0, 'ancre': 'Nom(s) et Prénom du demandeur', 'mode': 'dessous', 'dy': 2},
        {'cle': 'adresse', 'page': 0, 'ancre': 'Adresse :', 'x_min': D, 'mode': 'dessous', 'dy': 2, 'largeur': 480,
         'lignes': 2, 'interligne': 16},
        {'cle': 'cp_commune', 'page': 0, 'ancre': 'Code Postal et Commune', 'dx': 8},
        {'cle': 'nom_bailleur', 'page': 0, 'ancre': 'NOM et ADRESSE du bailleur', 'mode': 'dessous', 'dy': 2,
         'largeur': 480, 'lignes': 2, 'interligne': 16},
        {'cle': 'contact_bailleur', 'page': 0, 'ancre': 'Coordonnées téléphoniques et/ou adresse mail du bailleur',
         'dx': 40},
        {'cle': 'surendettement_oui', 'page': 0, 'ancre': 'OUI', 'ligne_de': 'Saisine Commission Surendettement'},
        {'cle': 'surendettement_non', 'page': 0, 'ancre': 'NON', 'ligne_de': 'Saisine Commission Surendettement'},
        {'cle': 'lg_typologie', 'page': 0, 'ancre': 'Typologie :', 'dx': 4},
        {'cle': 'lg_surface', 'page': 0, 'ancre': 'Surface :', 'dx': 4},
        {'cle': 'lg_loyer', 'page': 0, 'ancre': 'Loyer mensuel :', 'dx': 4},
        {'cle': 'lg_charges', 'page': 0, 'ancre': 'Charges :', 'dx': 4},
        {'cle': 'lg_garage', 'page': 0, 'ancre': 'Garage :', 'dx': 4},
        {'cle': 'lg_total', 'page': 0, 'ancre': 'Total :', 'dx': 4},
        {'cle': 'chauffage_oui', 'page': 0, 'ancre': 'OUI', 'ligne_de': 'Chauffage collectif'},
        {'cle': 'chauffage_non', 'page': 0, 'ancre': 'NON', 'ligne_de': 'Chauffage collectif'},
        {'cle': 'lg_al', 'page': 0, 'ancre': "Montant de l'AL ou APL :", 'dx': 4},
        {'cle': 'lg_rls', 'page': 0, 'ancre': 'Montant RLS :', 'dx': 4},
        {'cle': 'ccapex_non', 'page': 0, 'ancre': 'NON', 'ligne_de': 'Saisine de la CCAPEX'},
        {'cle': 'ccapex_oui', 'page': 0, 'ancre': 'OUI', 'ligne_de': 'Saisine de la CCAPEX'},
        {'cle': 'remise_oui', 'page': 1, 'ancre': 'OUI', 'ligne_de': 'consent-il'},
        {'cle': 'remise_non', 'page': 1, 'ancre': 'NON', 'ligne_de': 'consent-il'},
        {'cle': 'montant_remise', 'page': 1, 'ancre': 'indiquer le montant :', 'dx': 4},
        {'cle': 'titre_MAINTIEN', 'page': 0, 'ancre': 'MAINTIEN', 'dx': -2},
        {'cle': 'titre_CONCORDAT', 'page': 0, 'ancre': 'CONCORDAT', 'dx': -2},
        {'cle': 'variante_MAINTIEN', 'page': 1, 'ancre': 'FSL Maintien Reprise', 'mode': 'case', 'dx': -6},
        {'cle': 'variante_CONCORDAT', 'page': 1, 'ancre': 'FSL Concordat Reprise', 'mode': 'case', 'dx': -6},
        {'cle': 'ts_nom', 'page': 1, 'ancre': 'Nom du travailleur social', 'dx': 12},
        {'cle': 'ts_prenom', 'page': 1, 'ancre': 'Prénom :', 'x_min': D, 'top_min': 400, 'dx': 4},
        {'cle': 'ts_qualite', 'page': 1, 'ancre': 'Educateur spécialisé)', 'dx': 10},
        {'cle': 'ts_telephone', 'page': 1, 'ancre': 'ligne directe', 'dx': 10},
        {'cle': 'ts_portable', 'page': 1, 'ancre': 'téléphone portable', 'dx': 10},
        {'cle': 'ts_email', 'page': 1, 'ancre': 'Adresse mail TS', 'dx': 10},
        {'cle': 'ts_organisme', 'page': 1, 'ancre': "Nom et adresse de l'organisme", 'mode': 'dessous', 'dy': 6,
         'largeur': 520, 'lignes': 3, 'interligne': 21},
    ]
    return c


def _engagements():
    return [{'cle': 'num_caf', 'ancre': 'N° ALLOCATAIRE :', 'dx': 4},
            {'cle': 'reprise_depuis', 'ancre': 'paiement du loyer depuis le mois de :', 'mode': 'dessous', 'dx': 0, 'dy': 0},
            {'cle': 'total_loyer', 'ancre': 'soit un total de', 'dx': 6},
            {'cle': 'accompagnement', 'ancre': '(Nom, adresse, service social', 'mode': 'dessous', 'dy': 1,
             'largeur': 440, 'lignes': 2, 'interligne': 13, 'taille': 8},
            {'cle': 'bailleur', 'ancre': 'Le bailleur représenté par', 'dx': 6}]


def _convention_concordat():
    return [{'cle': 'num_caf', 'ancre': 'N° allocataire :', 'dx': 4},
            {'cle': 'locataires', 'ancre': 'Madame, Monsieur,', 'occ': 0, 'dx': 2},
            {'cle': 'reprise_depuis', 'ancre': 'de :', 'occ': 0, 'dx': 4},
            {'cle': 'total_loyer', 'ancre': 'soit un total de :', 'dx': 4},
            {'cle': 'accompagnement', 'ancre': '(Nom, adresse, service social', 'mode': 'dessous', 'dy': 0,
             'largeur': 440, 'lignes': 1, 'taille': 8},
            {'cle': 'bailleur', 'ancre': 'Le bailleur représenté par', 'dx': 4}]


def _liste_pieces_maintien():
    c = _identite_simple(caf='CAF13 :')
    ancres = {'avis': 'Avis motivé et proposition', 'formulaire': 'Formulaire dûment rempli',
              'identite': "Copie des justificatifs d'identité", 'etat_civil_mineurs': 'Pour les mineurs',
              'ressources': 'Copie des justificatifs des ressources de toutes',
              'ressources_majeurs': 'Copie des justificatifs de ressources ou non',
              'surendettement': "Copie de l'état d'avancement", 'rib': "Copie du Relevé d'Identité Bancaire ou postal",
              'bail': 'Copie du bail', 'assurance': "Copie de l'attestation d'assurance",
              'releve_compte': 'Relevé de compte locataire', 'contrat_pret': 'Contrat de prêt',
              'prelevement': 'Autorisation et demande de prélèvements', 'ident_logement': "Fiche d'identification du logement",
              'rib_bailleur': "Copie du Relevé d'identité bancaire, postal", 'kbis': 'Extrait K-bis',
              'engagements': 'Engagements du locataire et du bailleur', 'convention_concordat': 'Convention de résorption'}
    for code, ancre in ancres.items():
        c.append({'cle': f'piece_{code}', 'ancre': ancre, 'mode': 'case', 'dx': -4})
    return c


def _argumentaire_maintien():
    c = _identite_simple(caf='N° CAF :')
    ancres = {'identite': "Justificatifs d'état civil", 'ressources': 'Justificatifs des ressources de toutes',
              'ressources_majeurs': 'Justificatifs de ressources ou non', 'surendettement': 'Plan conventionnel',
              'rib': ("Relevé d'identité bancaire, postal ou", 0, 0, 290), 'bail': 'Photocopie du bail',
              'contrat_pret': 'Contrat de prêt signé', 'prelevement': 'Autorisation de prélèvement',
              'assurance': "Photocopie de l'attestation d'assurance", 'releve_compte': 'Relevé de compte locataire',
              'ident_logement': "Fiche d'identification du logement",
              'rib_bailleur': ("Relevé d'identité bancaire, postal ou", 0, 290, 1e6), 'kbis': 'Extrait K-bis',
              'versement_direct': 'Imprimé de demande de versement', 'engagements': 'engagements du locataire',
              'convention_concordat': 'Convention de résorption', 'ccapex': 'Justificatif de la saisine de la CCAPEX'}
    for code, ancre in ancres.items():
        if isinstance(ancre, tuple):
            texte, occ, xmin, xmax = ancre
            c.append({'cle': f'piece_{code}', 'ancre': texte, 'occ': occ, 'x_min': xmin, 'x_max': xmax,
                      'mode': 'case', 'dx': -11, 'dy': -3})
        else:
            c.append({'cle': f'piece_{code}', 'ancre': ancre, 'mode': 'case', 'dx': -11, 'dy': -3})
    c += [{'cle': 'note_cadre', 'ancre': 'NOTE EXPLICATIVE DU CADRE', 'mode': 'dessous', 'dx': -150, 'dy': 6,
           'largeur': 480, 'lignes': 14},
          {'cle': 'date', 'ancre': 'Fait le :', 'dx': 4},
          {'cle': 'cadre', 'ancre': 'signature du cadre social', 'mode': 'dessous', 'dy': 2, 'largeur': 230, 'lignes': 3}]
    return c


def _argumentaire_fluides(eau):
    """Liste à deux colonnes (énergie à gauche, eau à droite) : on coche dans la colonne du type de demande."""
    c = _identite_simple(caf='N° CAF :')
    x = {'x_min': 300} if eau else {'x_max': 300}
    for code, ancre in [('formulaire', 'Imprimé'), ('facture', 'Dernière facture impayée'),
                        ('identite', 'Copie de toutes pièces'), ('ressources', 'Justificatifs de ressources'),
                        ('quittance', 'Quittance de loyer'), ('surendettement', 'Plan conventionnel')]:
        c.append(dict({'cle': f'piece_{code}', 'ancre': ancre, 'mode': 'case', 'dx': -11, 'dy': -2}, **x))
    c += [{'cle': 'note_cadre', 'ancre': 'NOTE EXPLICATIVE DU CADRE', 'mode': 'dessous', 'dx': -150, 'dy': 6,
           'largeur': 480, 'lignes': 14},
          {'cle': 'date', 'ancre': 'Fait le :', 'dx': 4},
          {'cle': 'cadre', 'ancre': 'signature du cadre social', 'mode': 'dessous', 'dy': 2, 'largeur': 230, 'lignes': 3}]
    return c


def _identite_simple(prefixe_nom="Nom :", prenom="Prénom :", caf=None):
    c = [{'cle': 'nom', 'ancre': prefixe_nom, 'dx': 4}, {'cle': 'prenom', 'ancre': prenom, 'dx': 4}]
    if caf:
        c.append({'cle': 'num_caf', 'ancre': caf, 'dx': 4})
    return c


def _avis():
    return _identite_simple(caf='Allocataire :') + [
        {'cle': 'avis_FAVORABLE', 'ancre': 'Favorable', 'mode': 'case_dessous', 'dy': 3},
        {'cle': 'avis_RESERVE', 'ancre': 'Réservé', 'mode': 'case_dessous', 'dy': 3},
        {'cle': 'avis_DEFAVORABLE', 'ancre': 'Défavorable', 'mode': 'case_dessous', 'dy': 3},
        {'cle': 'avis_texte', 'ancre': 'Prénom :', 'mode': 'dessous', 'dx': 0, 'dy': 70, 'largeur': 500,
         'lignes': 38, 'taille': 9},
        {'cle': 'pret', 'ancre': 'Prêt :', 'dx': 4}, {'cle': 'subvention', 'ancre': 'Subvention :', 'dx': 4},
        {'cle': 'ts', 'ancre': 'Nom du Travailleur Social', 'dx': 10},
    ]


def _contrat():
    return [{'cle': 'demandeur', 'ancre': 'Demandeur :', 'dx': 4, 'taille': 8},
            {'cle': 'demandeur_naissance', 'ancre': 'Né(e) le :', 'occ': 0, 'dx': 4, 'taille': 8},
            {'cle': 'num_caf', 'ancre': 'N° CAF :', 'dx': 4, 'taille': 8},
            {'cle': 'conjoint', 'ancre': 'Conjoint', 'dx': 18, 'taille': 8},
            {'cle': 'conjoint_naissance', 'ancre': 'Né(e) le :', 'occ': 1, 'dx': 4, 'taille': 8},
            {'cle': 'vit_seul', 'ancre': 'Vivant seul', 'dx': 18}]


def _prelevement():
    return [{'cle': 'nom_prenom', 'ancre': 'Nom, prénom :', 'dx': 4},
            {'cle': 'adresse', 'ancre': 'Adresse :', 'occ': 0, 'top_min': 0, 'dx': 4},
            {'cle': 'num_caf', 'ancre': 'Allocataire C.A.F', 'dx': 10}]


def _convention():
    return [{'cle': 'bailleur', 'ancre': 'Le Bailleur :', 'dx': 4},
            {'cle': 'locataires', 'ancre': 'les locataires :', 'dx': 4},
            {'cle': 'num_caf', 'ancre': 'allocataire :', 'dx': 4},
            {'cle': 'domicile', 'ancre': 'Nouveau domicile :', 'dx': 4, 'largeur': 380, 'lignes': 2},
            {'cle': 'loyer', 'ancre': 'paiement du loyer', 'dx': 6},
            {'cle': 'charges', 'ancre': '+ charges', 'dx': 4},
            {'cle': 'total', 'ancre': 'soit au TOTAL', 'dx': 6},
            {'cle': 'accompagnement', 'ancre': 'désigné(s) ci-après', 'mode': 'dessous', 'dx': -330, 'dy': 4,
             'largeur': 420, 'lignes': 3, 'interligne': 13}]


def _ident_logement():
    return [{'cle': 'locataire', 'ancre': 'Prénom du locataire :', 'dx': 4},
            {'cle': 'adresse', 'ancre': 'Adresse du logement', 'dx': 10},
            {'cle': 'code_postal', 'ancre': 'Code postal :', 'occ': 0, 'dx': 4},
            {'cle': 'ville', 'ancre': 'Ville :', 'occ': 0, 'dx': 4},
            {'cle': 'num_caf', 'ancre': 'N° CAF :', 'dx': 4}]


PIECES_LISTE = {
    'formulaire': 'Formulaire dûment rempli', 'avis': 'Avis motivé et proposition',
    'identite': "Copie des justificatifs d'identité", 'etat_civil_mineurs': 'Pour les mineurs',
    'ressources': 'Copie des justificatifs des ressources de toutes',
    'ressources_majeurs': 'Copie des justificatifs de ressources ou non',
    'rib': "Copie du relevé d'identité bancaire ou postal", 'bail': 'Copie du bail',
    'etat_lieux': "Copie de l'état des lieux", 'assurance': "Copie de l'attestation d'assurance",
    'compteurs': 'Copie des justificatifs des ouvertures', 'caution_precedente': 'Copie du justificatif de restitution',
    'situation_precedente': 'Copie des justificatifs de la situation précédente', 'contrat_pret': 'Contrat de prêt',
    'prelevement': 'Autorisation et demande de prélèvements', 'garantie': 'Contrat de Mise en Jeu',
    'ident_logement': "Fiche d'identification du logement", 'rib_bailleur': "Copie du Relevé d'identité bancaire, postal",
    'kbis': 'Extrait K-bis', 'convention': "Convention d'accès au logement",
}
PIECES_ARGUMENTAIRE = {
    'identite': "Justificatifs d'état civil", 'ressources': 'Justificatifs des ressources de toutes',
    'ressources_majeurs': 'Justificatifs de ressources ou non', 'surendettement': 'Plan conventionnel',
    'rib': ("Relevé d'identité bancaire, postal ou", 0, 0, 290), 'bail': 'Photocopie du bail',
    'etat_lieux': "Photocopie de l'état des lieux", 'assurance': "Photocopie de l'attestation d'assurance",
    'compteurs': 'Justificatifs des ouvertures des compteurs', 'contrat_pret': 'Contrat de prêt signé',
    'prelevement': 'Autorisation de prélèvement', 'garantie': 'Contrat de Mise en Jeu',
    'ident_logement': "Fiche d'identification du logement", 'rib_bailleur': ("Relevé d'identité bancaire, postal ou", 0, 290, 1e6),
    'kbis': 'Extrait K-bis', 'convention': "Convention d'accès au logement", 'versement_direct': 'Demande de versement direct',
}


def _liste_pieces():
    c = _identite_simple(caf='CAF13 :')
    for code, ancre in PIECES_LISTE.items():
        c.append({'cle': f'piece_{code}', 'ancre': ancre, 'mode': 'case', 'dx': -4})
    return c


def _argumentaire():
    c = _identite_simple(caf='N° CAF :')
    for code, ancre in PIECES_ARGUMENTAIRE.items():
        if isinstance(ancre, tuple):
            texte, occ, xmin, xmax = ancre
            c.append({'cle': f'piece_{code}', 'ancre': texte, 'occ': occ, 'x_min': xmin, 'x_max': xmax,
                      'mode': 'case', 'dx': -11})
        else:
            c.append({'cle': f'piece_{code}', 'ancre': ancre, 'mode': 'case', 'dx': -11})
    c += [{'cle': 'note_cadre', 'ancre': 'NOTE EXPLICATIVE DU CADRE', 'mode': 'dessous', 'dx': -150, 'dy': 6,
           'largeur': 480, 'lignes': 14},
          {'cle': 'date', 'ancre': 'Fait le :', 'dx': 4},
          {'cle': 'cadre', 'ancre': 'signature du cadre social', 'mode': 'dessous', 'dy': 2, 'largeur': 230, 'lignes': 3}]
    return c


def _cerfa_11362():
    return [{'cle': 'nom', 'ancre': 'Nom', 'occ': 0, 'top_min': 330, 'mode': 'apres', 'dx': 4},
            {'cle': 'prenom', 'ancre': 'Prénom', 'top_min': 330, 'dx': 4},
            {'cle': 'adresse', 'ancre': 'Adresse', 'top_min': 330, 'dx': 4},
            {'cle': 'code_postal', 'ancre': 'Code postal', 'top_min': 330, 'dx': 4},
            {'cle': 'commune', 'ancre': 'Commune', 'top_min': 330, 'dx': 4},
            {'cle': 'num_caf', 'ancre': "N° d'allocataire", 'dx': 30}]


def placements(code, type_aide=None):
    from logement.models import FormulaireOfficiel as F
    if code == F.ARGUMENTAIRE_FLUIDES:
        return _argumentaire_fluides(type_aide == 'EAU')
    return {F.FORMULAIRE_ACCES: _formulaire_acces, F.AVIS_MOTIVE: _avis, F.CONTRAT_PRET: _contrat,
            F.CONTRAT_GARANTIE: _contrat, F.PRELEVEMENT: _prelevement, F.CONVENTION_ACCES: _convention,
            F.IDENTIFICATION_LOGEMENT: _ident_logement, F.LISTE_PIECES: _liste_pieces,
            F.ARGUMENTAIRE: _argumentaire, F.VERSEMENT_DIRECT_AL: _cerfa_11362,
            F.FORMULAIRE_EAU: lambda: _formulaire_fluides(True), F.FORMULAIRE_ENERGIE: lambda: _formulaire_fluides(False),
            F.AVIS_FLUIDES: _avis, F.ARGUMENTAIRE_FLUIDES: lambda: _argumentaire_fluides(False),
            F.FORMULAIRE_MAINTIEN: _formulaire_maintien, F.ARGUMENTAIRE_MAINTIEN: _argumentaire_maintien,
            F.ENGAGEMENTS: _engagements, F.CONVENTION_CONCORDAT: _convention_concordat,
            F.LISTE_PIECES_MAINTIEN: _liste_pieces_maintien}[code]()


# ---------------------------------------------------------------------------------------------------------------
# Valeurs à écrire, à partir de la demande

def _nom(p):
    return f"{(p.get('nom') or '').upper()} {p.get('prenom') or ''}".strip()


def valeurs(demande, code, aujourdhui=None):
    from django.utils import timezone
    from logement.models import FormulaireOfficiel as F
    dn = demande.donnees or {}
    comp = dn.get('composition') or []
    dem = comp[0] if comp else {}
    conj = next((p for p in comp if p.get('role') == 'CONJOINT'), None)
    ts = dn.get('ts') or {}
    jour = (aujourdhui or timezone.localdate()).strftime('%d/%m/%Y')
    b = demande.beneficiaire
    if code == F.FORMULAIRE_ACCES:
        v = {'bailleur_social': dn.get('bailleur_type') == 'SOCIAL', 'bailleur_prive': dn.get('bailleur_type') == 'PRIVE',
             'num_caf': dn.get('num_caf'), 'autres_numero': dn.get('autres_numero'),
             'demandeur': " – ".join(_nom(p) for p in [dem, conj] if p),
             'adresse_objet': dn.get('adresse_objet'), 'cp_commune': dn.get('cp_commune'),
             'nouveau_bailleur': dn.get('nouveau_bailleur'), 'contact_bailleur': dn.get('contact_bailleur'),
             f"sf_{dn.get('situation_familiale')}": bool(dn.get('situation_familiale'))}
        enfants = [p for p in comp if p.get('role') == 'ENFANT'][:5]
        autres = [p for p in comp if p.get('role') == 'AUTRE'][:2]
        lignes = [dem, conj] + enfants + [None] * (5 - len(enfants)) + autres
        for i, p in enumerate(lignes[:9]):
            if not p:
                continue
            for col in ('nom', 'prenom', 'date_naissance', 'nationalite'):
                v[f'comp_{i}_{col}'] = p.get(col)
            situation = p.get('situation') or ''
            v[f'comp_{i}_situation'] = f"{situation} ({p['lien']})" if p.get('lien') else situation
        res = dn.get('ressources') or {}
        for code_r, _, _ in RESSOURCES_FSL:
            for col, _ in COLONNES:
                v[f'res_{code_r}_{col}'] = montant((res.get(code_r) or {}).get(col))
        for code_r, texte in (dn.get('ressources_precisions') or {}).items():
            v[f'prec_{code_r}'] = texte
        par_col, total = totaux_ressources(res)
        for col, _ in COLONNES:
            v[f'total_{col}'] = montant(par_col[col])
        v['total_ressources'] = montant(total)
        v['quotient_familial'] = dn.get('quotient_familial')
        v['taux_effort'] = taux_effort(dn)
        for cle, val in (dn.get('logement_anterieur') or {}).items():
            v[f'ant_{cle}'] = montant(val) if cle in ('loyer', 'charges', 'al', 'loyer_residuel') else val
        caution = (dn.get('logement_anterieur') or {}).get('caution_restituee')
        v['ant_caution_oui'], v['ant_caution_non'] = ("X" if caution == 'OUI' else ''), ("X" if caution == 'NON' else '')
        for cle, val in (dn.get('logement_nouveau') or {}).items():
            v[f'nv_{cle}'] = montant(val) if cle in ('loyer', 'charges', 'montant_caution', 'al_previsionnel', 'loyer_residuel') else val
        chauffage = (dn.get('logement_nouveau') or {}).get('chauffage_collectif')
        v['nv_chauffage_oui'], v['nv_chauffage_non'] = ("X" if chauffage == 'OUI' else ''), ("X" if chauffage == 'NON' else '')
        v[f"garantie_{dn.get('garantie')}"] = bool(dn.get('garantie'))
        prop = dn.get('proposition') or {}
        for code_p, _ in PROPOSITION:
            v[f'prop_{code_p}'] = montant(prop.get(code_p))
            v[f'case_{code_p}'] = bool(d(prop.get(code_p)))
        for code_e, _ in EQUIPEMENTS:
            v[f'eq_{code_e}'] = code_e in (dn.get('equipements') or [])
        for cle in ('nom', 'prenom', 'qualite', 'telephone', 'portable', 'email', 'organisme'):
            v[f'ts_{cle}'] = ts.get(cle)
        return v
    if code in (F.FORMULAIRE_EAU, F.FORMULAIRE_ENERGIE):
        v = valeurs(demande, F.FORMULAIRE_ACCES, aujourdhui)
        v = {k: x for k, x in v.items() if not k.startswith(('prop_', 'case_', 'eq_', 'garantie_', 'ant_', 'nv_'))}
        v.update({'distributeur': dn.get('distributeur'), 'adresse': dn.get('adresse'),
                  'montant_loyer': montant(dn.get('montant_loyer')), f"sl_{dn.get('situation_logement')}": bool(dn.get('situation_logement')),
                  'charges_exceptionnelles': dn.get('charges_exceptionnelles'),
                  'surendettement_oui': dn.get('surendettement') == 'OUI', 'surendettement_non': dn.get('surendettement') == 'NON',
                  'commentaire_administratif': dn.get('commentaire_administratif') if demande.instruction_administrative else '',
                  'date_facture': dn.get('date_facture'), 'montant_facture': montant(dn.get('montant_facture')),
                  'dette_electricite': montant(dn.get('dette_electricite')), 'dette_gaz': montant(dn.get('dette_gaz')),
                  'participation_oui': dn.get('participation') == 'OUI', 'participation_non': dn.get('participation') == 'NON',
                  'plan_fournisseur': dn.get('plan_fournisseur')})
        return v
    if code == F.FORMULAIRE_MAINTIEN:
        v = valeurs(demande, F.FORMULAIRE_ACCES, aujourdhui)
        v = {k: x for k, x in v.items() if not k.startswith(('prop_', 'case_', 'eq_', 'garantie_', 'ant_', 'nv_'))}
        lg = dn.get('logement') or {}
        total = d(lg.get('loyer')) + d(lg.get('charges')) + d(lg.get('garage'))
        v.update({'adresse': dn.get('adresse'), 'nom_bailleur': dn.get('nom_bailleur'),
                  'surendettement_oui': "X" if dn.get('saisine_surendettement') == 'OUI' else '',
                  'surendettement_non': "X" if dn.get('saisine_surendettement') == 'NON' else '',
                  'lg_typologie': lg.get('typologie'), 'lg_surface': lg.get('surface'),
                  'lg_loyer': montant(lg.get('loyer')), 'lg_charges': montant(lg.get('charges')),
                  'lg_garage': montant(lg.get('garage')), 'lg_total': montant(total),
                  'lg_al': montant(lg.get('al')), 'lg_rls': montant(lg.get('rls')),
                  'chauffage_oui': "X" if dn.get('chauffage_collectif') == 'OUI' else '',
                  'chauffage_non': "X" if dn.get('chauffage_collectif') == 'NON' else '',
                  'ccapex_oui': "X" if dn.get('saisine_ccapex') == 'OUI' else '',
                  'ccapex_non': "X" if dn.get('saisine_ccapex') == 'NON' else '',
                  'remise_oui': "X" if dn.get('remise_dette') == 'OUI' and demande.est_concordat else '',
                  'remise_non': "X" if dn.get('remise_dette') == 'NON' and demande.est_concordat else '',
                  'montant_remise': montant(dn.get('montant_remise')) if demande.est_concordat else '',
                  f"variante_{dn.get('variante')}": bool(dn.get('variante')),
                  f"titre_{dn.get('variante')}": "X" if dn.get('variante') else ''})
        return v
    if code in (F.ENGAGEMENTS, F.CONVENTION_CONCORDAT):
        lg = dn.get('logement') or {}
        total = d(lg.get('loyer')) + d(lg.get('charges')) + d(lg.get('garage'))
        acc = (f"{ts.get('prenom', '')} {ts.get('nom', '')}, {ts.get('qualite', '')} – {ts.get('organisme', '')} – "
               f"{ts.get('telephone', '')}").strip(" ,–")
        return {'num_caf': dn.get('num_caf'), 'reprise_depuis': dn.get('reprise_paiement_depuis'),
                'total_loyer': montant(total), 'accompagnement': acc,
                'bailleur': (dn.get('nom_bailleur') or '').split("\n")[0],
                'locataires': " – ".join(_nom(p) for p in [dem, conj] if p)}
    if code == F.LISTE_PIECES_MAINTIEN:
        code = F.LISTE_PIECES
    if code == F.ARGUMENTAIRE_MAINTIEN:
        code = F.ARGUMENTAIRE
    if code == F.AVIS_FLUIDES:
        code = F.AVIS_MOTIVE
    if code == F.ARGUMENTAIRE_FLUIDES:
        code = F.ARGUMENTAIRE
    if code == F.AVIS_MOTIVE:
        return {'nom': dem.get('nom'), 'prenom': dem.get('prenom'), 'num_caf': dn.get('num_caf'),
                f'avis_{demande.avis}': bool(demande.avis), 'avis_texte': demande.avis_motive,
                'pret': montant(demande.proposition_pret), 'subvention': montant(demande.proposition_subvention),
                'ts': f"{ts.get('prenom', '')} {ts.get('nom', '')}".strip()}
    if code in (F.CONTRAT_PRET, F.CONTRAT_GARANTIE):
        return {'demandeur': _nom(dem), 'demandeur_naissance': dem.get('date_naissance'), 'num_caf': dn.get('num_caf'),
                'conjoint': _nom(conj) if conj else '', 'conjoint_naissance': conj.get('date_naissance') if conj else '',
                'vit_seul': "X" if not conj else ''}
    if code == F.PRELEVEMENT:
        return {'nom_prenom': _nom(dem), 'adresse': dn.get('adresse_objet') or dn.get('adresse_actuelle'),
                'num_caf': dn.get('num_caf')}
    if code == F.CONVENTION_ACCES:
        n = dn.get('logement_nouveau') or {}
        total = d(n.get('loyer')) + d(n.get('charges'))
        return {'bailleur': n.get('bailleur') or dn.get('nouveau_bailleur', '').split("\n")[0],
                'locataires': " – ".join(_nom(p) for p in [dem, conj] if p), 'num_caf': dn.get('num_caf'),
                'domicile': " ".join(x for x in [dn.get('adresse_objet'), dn.get('cp_commune')] if x),
                'loyer': montant(n.get('loyer')), 'charges': montant(n.get('charges')), 'total': montant(total),
                'accompagnement': f"{ts.get('prenom', '')} {ts.get('nom', '')}, {ts.get('qualite', '')} – "
                                  f"{ts.get('organisme', '')} – {ts.get('telephone', '')}".strip(" ,–")}
    if code == F.IDENTIFICATION_LOGEMENT:
        cp_ville = (dn.get('cp_commune') or '').split(' ', 1)
        return {'locataire': _nom(dem), 'adresse': dn.get('adresse_objet') or dn.get('adresse'), 'code_postal': cp_ville[0],
                'ville': cp_ville[1] if len(cp_ville) > 1 else '', 'num_caf': dn.get('num_caf')}
    if code in (F.LISTE_PIECES, F.ARGUMENTAIRE):
        v = {'nom': dem.get('nom'), 'prenom': dem.get('prenom'), 'num_caf': dn.get('num_caf')}
        for c, etat in (demande.pieces or {}).items():
            v[f'piece_{c}'] = etat == 'FOURNIE'
        if code == F.ARGUMENTAIRE:
            v['note_cadre'] = demande.note_cadre
            v['date'] = demande.date_validation_cadre.strftime('%d/%m/%Y') if demande.date_validation_cadre else ''
            if demande.cadre:
                from mds.fonctions import nom_et_fonction
                v['cadre'] = nom_et_fonction(demande.cadre, demande.mds, "\n")
        return v
    if code == F.VERSEMENT_DIRECT_AL:
        cp_ville = (dn.get('cp_commune') or '').split(' ', 1)
        return {'nom': (dem.get('nom') or '').upper(), 'prenom': dem.get('prenom'),
                'adresse': dn.get('adresse_objet') or dn.get('adresse'),
                'code_postal': cp_ville[0], 'commune': cp_ville[1] if len(cp_ville) > 1 else '', 'num_caf': dn.get('num_caf')}
    return {}
