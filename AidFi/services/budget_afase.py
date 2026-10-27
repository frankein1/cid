# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/services/budget_afase.py
"""
Budget mensuel du ménage, rubriques du formulaire de demande d'AFASE :
  - ressources ventilées demandeur / conjoint / autres ;
  - charges liées au logement et autres charges, chacune payée ou non payée ;
  - dettes du ménage (créancier, montant).
Reste à vivre = (total des ressources − total des charges PAYÉES) / nombre de personnes au foyer / 30.

Format enregistré (JSON) :
  ressources = {"v": 2, "lignes": {code: {"demandeur": x, "conjoint": y, "autres": z}}, "precisions": {code: "…"}}
  charges    = {"v": 2, "lignes": {code: {"payee": x, "non_payee": y}}, "precisions": {code: "…"}}
Les budgets saisis avant (lignes libres {libellé: montant}) restent lisibles : format « ancien ».
"""
from decimal import Decimal, InvalidOperation

COLONNES_RESSOURCES = [('demandeur', "Demandeur"), ('conjoint', "Conjoint"), ('autres', "Autres")]
COLONNES_CHARGES = [('payee', "Payées"), ('non_payee', "Non payées")]

RESSOURCES = [
    ("Revenus liés à l'activité", [
        ('salaire', "Salaire net avant impôt (y compris apprentissage et stages rémunérés)"),
        ('ij', "Indemnités journalières"),
        ('chomage', "Indemnités de chômage (ARE, ASS…)"),
        ('rsa', "RSA"),
        ('retraite', "Retraites et allocations personnes âgées (principale, complémentaire, ASPA…)"),
        ('autres_activite', "Autres (à préciser)"),
    ]),
    ("Prestations sociales", [
        ('logement', "Allocations logement (AL, APL, ALS, ALF, RLS)"),
        ('familiales', "Allocations familiales"),
        ('aah', "AAH et complément AAH, PCH, AEEH"),
        ('prepare', "PreParE"),
        ('ada', "ADA"),
        ('bourses', "Bourses d'études"),
        ('autres_prestations', "Autres (à préciser)"),
    ]),
    ("Pensions", [
        ('pension_alimentaire', "Pension alimentaire"),
        ('invalidite', "Pension d'invalidité (ou autres, à préciser)"),
    ]),
]
CHARGES = [
    ("Charges liées au logement", [
        ('loyer', "Loyer charges comprises"),
        ('accession', "Accession à la propriété"),
        ('electricite', "Électricité"),
        ('combustibles', "Combustibles"),
        ('assurance_habitation', "Assurance habitation"),
        ('taxes_logement', "Taxes"),
        ('autres_logement', "Autres (à préciser)"),
    ]),
    ("Autres charges", [
        ('telephone', "Téléphone, internet et autres abonnements"),
        ('assurances', "Assurances (hors assurance habitation)"),
        ('pensions_versees', "Pensions alimentaires"),
        ('garde_scolarite', "Frais de garde et de scolarité (dont cantine et transports scolaires)"),
        ('impots', "Impôts et taxes"),
        ('credits', "Mensualités crédits"),
        ('autres_charges', "Autres (à préciser)"),
    ]),
]
A_PRECISER = {'autres_activite', 'autres_prestations', 'invalidite', 'autres_logement', 'autres_charges'}


def _d(valeur):
    try:
        return Decimal(str(valeur).replace(',', '.').strip() or 0)
    except (InvalidOperation, ValueError):
        return Decimal(0)


def est_nouveau(data):
    return isinstance(data, dict) and data.get('v') == 2


def depuis_post(post):
    """Lit les champs du formulaire (r__salaire__demandeur, c__loyer__payee, d__0__creancier…)."""
    ressources = {'v': 2, 'lignes': {}, 'precisions': {}}
    for _, lignes in RESSOURCES:
        for code, _ in lignes:
            valeurs = {col: str(_d(post.get(f'r__{code}__{col}'))) for col, _ in COLONNES_RESSOURCES}
            if any(_d(v) for v in valeurs.values()):
                ressources['lignes'][code] = valeurs
            if code in A_PRECISER and (post.get(f'r__{code}__precision') or '').strip():
                ressources['precisions'][code] = post.get(f'r__{code}__precision').strip()[:120]
    charges = {'v': 2, 'lignes': {}, 'precisions': {}}
    for _, lignes in CHARGES:
        for code, _ in lignes:
            valeurs = {col: str(_d(post.get(f'c__{code}__{col}'))) for col, _ in COLONNES_CHARGES}
            if any(_d(v) for v in valeurs.values()):
                charges['lignes'][code] = valeurs
            if code in A_PRECISER and (post.get(f'c__{code}__precision') or '').strip():
                charges['precisions'][code] = post.get(f'c__{code}__precision').strip()[:120]
    dettes = []
    for i in range(20):
        creancier = (post.get(f'd__{i}__creancier') or '').strip()
        montant = _d(post.get(f'd__{i}__montant'))
        if creancier or montant:
            dettes.append({'creancier': creancier[:120], 'montant': str(montant)})
    return ressources, charges, dettes


def totaux(ressources, charges, nb_personnes):
    """Totaux et reste à vivre journalier par personne. Ancien format : toutes les charges comptent."""
    nb = max(int(nb_personnes or 1), 1)
    if est_nouveau(ressources) or est_nouveau(charges):
        r = ressources.get('lignes', {}) if est_nouveau(ressources) else {}
        c = charges.get('lignes', {}) if est_nouveau(charges) else {}
        par_colonne = {col: sum((_d(v.get(col)) for v in r.values()), Decimal(0)) for col, _ in COLONNES_RESSOURCES}
        total_r = sum(par_colonne.values(), Decimal(0))
        logement = {code for code, _ in CHARGES[0][1]}
        payees_logement = sum((_d(v.get('payee')) for k, v in c.items() if k in logement), Decimal(0))
        payees_autres = sum((_d(v.get('payee')) for k, v in c.items() if k not in logement), Decimal(0))
        non_payees = sum((_d(v.get('non_payee')) for v in c.values()), Decimal(0))
        payees = payees_logement + payees_autres
    else:
        par_colonne = {}
        total_r = sum((_d(v) for v in (ressources or {}).values()), Decimal(0))
        payees = sum((_d(v) for v in (charges or {}).values()), Decimal(0))
        payees_logement = payees_autres = non_payees = Decimal(0)
    rav = ((total_r - payees) / nb / 30).quantize(Decimal('0.01'))
    return {'ressources': total_r, 'par_colonne': par_colonne, 'charges_payees': payees,
            'charges_logement_payees': payees_logement, 'autres_charges_payees': payees_autres,
            'charges_non_payees': non_payees, 'nb_personnes': nb, 'reste_a_vivre': rav,
            'solde': total_r - payees}


def lignes_affichage(ressources, charges):
    """Pour l'affichage et le PDF : [(titre, [(libellé, {colonne: montant})])], ancien format compris."""
    if not (est_nouveau(ressources) or est_nouveau(charges)):
        return {'ancien': True,
                'ressources': [(k, _d(v)) for k, v in (ressources or {}).items()],
                'charges': [(k, _d(v)) for k, v in (charges or {}).items()]}
    def bloc(referentiel, data, colonnes):
        lignes = data.get('lignes', {}) if est_nouveau(data) else {}
        prec = data.get('precisions', {}) if est_nouveau(data) else {}
        sortie = []
        for titre, items in referentiel:
            rangs = [((lib + (f" : {prec[code]}" if prec.get(code) else "")),
                      {col: _d(lignes[code].get(col)) for col, _ in colonnes})
                     for code, lib in items if code in lignes]
            if rangs:
                sortie.append((titre, rangs))
        return sortie
    return {'ancien': False, 'ressources': bloc(RESSOURCES, ressources, COLONNES_RESSOURCES),
            'charges': bloc(CHARGES, charges, COLONNES_CHARGES)}


def grille(ressources, charges):
    """Valeurs initiales du formulaire : {nom_du_champ: valeur}."""
    valeurs = {}
    if est_nouveau(ressources):
        for code, cols in ressources.get('lignes', {}).items():
            for col, v in cols.items():
                valeurs[f'r__{code}__{col}'] = v
        for code, p in ressources.get('precisions', {}).items():
            valeurs[f'r__{code}__precision'] = p
    if est_nouveau(charges):
        for code, cols in charges.get('lignes', {}).items():
            for col, v in cols.items():
                valeurs[f'c__{code}__{col}'] = v
        for code, p in charges.get('precisions', {}).items():
            valeurs[f'c__{code}__precision'] = p
    return valeurs
