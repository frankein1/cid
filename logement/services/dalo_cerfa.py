# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/dalo_cerfa.py
"""Remplissage du Cerfa 15036*02 (recours amiable DALO), formulaire PDF remplissable livré avec CID.

Les champs texte sont désignés par leur nom dans le PDF. Les cases sont désignées par leur nom technique
(« Case à cocher N ») repéré sur le formulaire, avec son libellé. Les sections 6 (ressources) et 7 (lieux de
travail) sont remplissables comme le reste. Ne sont pas remplies : la déclaration sur l'honneur (rubrique 11), à
signer à la main. La rubrique 10.2 de l'ancienne version du Cerfa n'existe pas dans la version 15036*02 ; la personne
qui aide le requérant est rubrique 9."""
import io
import re
from datetime import date
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

CERFA = Path(__file__).resolve().parent.parent / "formulaires" / "cerfa_15036-02_dalo.pdf"

CASES = {
    'civilite': {'MME': 'Case à cocher 8', 'M': 'Case à cocher 9'},
    'nationalite': {'FR': 'Case à cocher 17', 'UE': 'Case à cocher 18', 'HORS_UE': 'Case à cocher 19'},
    'logement': {'PROPRIETAIRE': 'Case à cocher 24', 'SOCIAL': 'Case à cocher 25',
                 'PRIVE': 'Case à cocher 26', 'AUTRE': 'Case à cocher 27'},
    'situations': {'DEPOURVU': 'Case à cocher 38', 'HEBERGE': 'Case à cocher 45', 'EXPULSION': 'Case à cocher 50',
                   'STRUCTURE': 'Case à cocher 55', 'INSALUBRE': 'Case à cocher 56', 'NON_DECENT': 'Case à cocher 59',
                   'TRANSITION': 'Case à cocher 83', 'SUROCCUPE': '8 logement sur-occupé',
                   'DELAI': 'Case à cocher 75'},
    'pcb': {'OUI': 'Case à cocher 34', 'NON': 'Case à cocher 35'},
    'surendettement': {'OUI': 'Case à cocher 36', 'NON': 'Case à cocher 37'},
}
NB_LIGNES_PERSONNES = 8

# Rubrique 6 : une ligne par nature de ressource, une colonne par personne (vous-même, autres personnes 1 à 3).
# Noms exacts des champs du PDF. None : champ absent ou dupliqué dans le PDF officiel, à remplir à la main.
RESSOURCES_PDF = [
    ('SALAIRE', {'vous': '6. Salaire vous-même', 'p1': '6. Salaire autre personne 1', 'p2': '6. Salaire autre personne 2', 'p3': '6. Salaire autre personne 3'}),
    ('RETRAITE', {'vous': '6. Retraite vous-même', 'p1': '6. Retraite autre personne 1', 'p2': '6. Retraite autre personne 2', 'p3': '6. Retraite autre personne 3'}),
    ('CHOMAGE', {'vous': '6. Chomage vous-même', 'p1': '6. Chomage autre personne 1', 'p2': 'Chomage autre personne 2', 'p3': '6. Chomage autre personne 3'}),
    ('PENSION', {'vous': '6. Pension vous-même', 'p1': '6. Pension autre personne 1', 'p2': '6. Pension autre personne 2', 'p3': '6. Pension autre personne 3'}),
    ('PENSION_INVALIDITE', {'vous': '6. Pension invalidité vous-même', 'p1': None, 'p2': None, 'p3': '6. Pension invalidité autre personne 3'}),
    ('ALLOCATIONS', {'vous': '6. Allocations vous-même', 'p1': '6. Allocations autre personne 1', 'p2': '6. Allocations autre personne 2', 'p3': '6. Allocations autre personne 3'}),
    ('AAH', {'vous': '6. AAH vous-même', 'p1': '6. AAH autre personne 1', 'p2': '6. AAH autre personne 2', 'p3': '6. AAH autre personne 3'}),
    ('AEEH', {'vous': '6. AEEH vous-même', 'p1': '6. AEEH autre personne 1', 'p2': '6. AEEH autre personne 2', 'p3': '6. AEEH autre personne 3'}),
    ('AJPP', {'vous': '6. AJPP vous-même', 'p1': '6. AJPP autre personne 1', 'p2': '6. AJPP autre personne 2', 'p3': '6. AJPP autre personne 3'}),
    ('RSA', {'vous': '6. RSA vous-même', 'p1': '6. RSA autre personne 1', 'p2': '6. RSA autre personne 2', 'p3': '6. RSA autre personne 3'}),
    ('PAJE', {'vous': '6. PAJE vous-même', 'p1': '6. PAJE autre personne 1', 'p2': '6. PAJE autre personne 2', 'p3': '6. PAJE autre personne 3'}),
    ('ASPA', {'vous': '6. AMV vous-même', 'p1': '6. AMV autre personne 1', 'p2': '6. AMV autre personne 2', 'p3': '6. AMV autre personne 3'}),
    ('BOURSE', {'vous': '6. Bourse étudiant vous-même', 'p1': '6. Bourse étudiant autre personne 1', 'p2': '6. Bourse étudiant autre personne 2', 'p3': '6. Bourse étudiant autre personne 3'}),
    ('PENSION_VERSEE', {'vous': '6. Pension que vous versez vous même', 'p1': '6. Pension que vous versez autre personne 1', 'p2': '6. Pension que vous versez autre personne 2', 'p3': '6. Pension que vous versez autre personne 3'}),
    ('PRIME_ACTIVITE', {'vous': '6. Prime activité versée vous-même', 'p1': '6. Prime activité versée autre personne 1', 'p2': '6. Prime activité versée autre personne 2', 'p3': '6. Prime activité versée autre personne 3'}),
    ('ABSENCE', {'vous': '6. Absence ressources vous-même', 'p1': '6. Absence ressources autre personne 1', 'p2': '6. Absence ressources autre personne 2', 'p3': '6. Absence ressources autre personne 3'}),
    ('AUTRES', {'vous': '6. Autres vous-même', 'p1': 'Autres autre personne 1', 'p2': '6. Autres autre personne 2', 'p3': '6. Autres autre personne 3'}),
]

# Rubrique 7 : ligne 0 = vous-même (pas de champ nom), lignes 1 à 7 = personnes du tableau 5.
# Lignes 5 et 6 : le champ « type de contrat » est dupliqué dans le PDF officiel, il n'est pas rempli.
LIEUX_PDF = [
    {'nom': None, 'activite': '7. Lieu de travail - Activite', 'contrat': '7. Type contrat',
     'entreprise': '8. Lieu de travail - Entreprise', 'commune': '7. Lieu de travail - Commune',
     'transport': '7. Lieu de travail - Moyen transport', 'temps': '7. Lieu de travail - Temps transport'},
]
for _i in range(1, 8):
    LIEUX_PDF.append({
        'nom': f'7. Lieu de travail - Nom {_i}', 'activite': f'7. Lieu de travail - Activite {_i}',
        'contrat': None if _i in (5, 6) else f'7. Type contrat L{_i}',  # 5 et 6 : voir plus bas
        'entreprise': f'7. Lieu de travail - Entreprise {_i}', 'commune': f'7. Lieu de travail - Commune {_i}',
        'transport': f'7. Lieu de travail - Moyen transport {_i}', 'temps': f'7. Lieu de travail - Temps transport {_i}'})
CONTRAT_PDF = {'CDI': 'CDI', 'CDD': 'CDD', 'INTERIM': 'Intérim', 'AUTRES': 'Autres'}


def _personnes(texte):
    """Lignes « Nom;Prénom;JJ/MM/AAAA;Lien » -> liste de tuples (8 maximum, les autres sont à joindre)."""
    lignes = []
    for ligne in (texte or '').splitlines():
        morceaux = [m.strip() for m in ligne.split(';')]
        if any(morceaux):
            morceaux += [''] * (4 - len(morceaux))
            lignes.append(tuple(morceaux[:4]))
    return lignes


def _cases_unitaires(valeur):
    """Dates et téléphones : le formulaire imprime barres et tirets, on n'écrit que les chiffres."""
    return re.sub(r'\D', '', valeur or '')


def valeurs(r):
    """Dictionnaire {nom du champ PDF: texte} et ensemble des cases à cocher, à partir du RecoursDALO."""
    txt = {
        '1. Nom de naissance': r.nom_naissance, "1. Nom d'usage": r.nom_usage, '1. Prenom(s)': r.prenoms,
        '1. Date de naissance': r.date_naissance, '1. Téléphone domicile': r.telephone,
        '1. Téléphone portable': r.telephone_portable, '1. Adresse électronique personnel 1/2': r.email,
        "2. Numéro unique d'enregistrement": r.nud,
        '3.1 Numéro': r.adresse_numero, '3.1 Voie': r.adresse_voie, "3.1 Complément d'adresse": r.adresse_complement,
        '3.1 Pays': 'France', '3.1 Commune': r.commune, '3. Code postal 1': r.code_postal,
        '3. Nom du bailleur figurant sur la quittance': r.bailleur, '3. Précisez': r.logement_autre,
        '6. Numero allocataire': r.numero_allocataire,
        '8. precisez nature local': r.nature_local,
        '8.2 personnes qui vous hebergent': r.hebergeurs, '8.2 nombre de personnes': r.hebergement_nb_personnes,
        '8.2 surface': r.hebergement_surface, '8.2 Pieces': r.hebergement_pieces,
        '8.4 nom de la structure': r.structure_nom, "8. Date d'entrée structure": r.structure_date,
        '8.8 surface totale logement': r.surface_totale, '8.8 nombres de pièces': r.nombre_pieces,
        '9. Nom personne': r.assistant_nom, '9. Nom de la structure': r.assistant_organisme,
        '9. numéro': r.assistant_adresse_numero, '9. Voie': r.assistant_adresse_voie,
        '9. Code postal': r.assistant_code_postal, '9. Commune': r.assistant_commune,
        '9. Tel pro': r.assistant_telephone,
        '10. Argumentaire libre 2': r.argumentaire,
        '11. Fait à': r.assistant_commune, '11. Fait le': date.today().strftime('%d/%m/%Y'),
    }
    for cle in ('1. Date de naissance', '1. Téléphone domicile', '1. Téléphone portable', '9. Tel pro',
                '8. Date d\'entrée structure'):
        txt[cle] = _cases_unitaires(txt[cle])
    personnes = _personnes(r.personnes)
    txt['5. nombre personnes'] = str(len(personnes)) if personnes else ''
    for i, (nom, prenom, naissance, lien) in enumerate(personnes[:NB_LIGNES_PERSONNES], start=1):
        txt[f'5. Nom L{i}'], txt[f'5. Prénom L{i}'] = nom, prenom
        txt[f'5. Date naissance L{i}'], txt[f'5. Lien de parenté L{i}'] = _cases_unitaires(naissance), lien
    txt['6. Ressources'] = r.ressources_mois
    txt['6. annee dernier avis'] = r.ressources_annee_avis
    for code, colonnes in RESSOURCES_PDF:
        for colonne, champ in colonnes.items():
            montant = (r.ressources or {}).get(f'{code}|{colonne}', '')
            if champ and montant:
                txt[champ] = montant
    lieux = list(r.lieux_travail or [])
    for i, champs in enumerate(LIEUX_PDF):
        ligne = lieux[i] if i < len(lieux) and isinstance(lieux[i], dict) else {}
        for cle, champ in champs.items():
            valeur = ligne.get(cle, '')
            if cle == 'contrat':
                # Le formulaire pré-sélectionne « CDI » partout : une ligne vide doit rester vide.
                if champ:
                    txt[champ] = CONTRAT_PDF.get(valeur, '')
                continue
            if champ and valeur:
                txt[champ] = valeur
    txt['7. Type contrat L6'] = ''  # champ partagé par les lignes 5 et 6 : non rempli
    cases = set()
    for cle, valeur in (('civilite', r.civilite), ('nationalite', r.nationalite), ('logement', r.logement),
                        ('pcb', r.pcb), ('surendettement', r.surendettement)):
        if valeur in CASES[cle]:
            cases.add(CASES[cle][valeur])
    cases |= {CASES['situations'][s] for s in r.situations if s in CASES['situations']}
    return {k: (v or '') for k, v in txt.items()}, cases


def remplir(r):
    """Octets du Cerfa 15036*02 rempli (formulaire toujours modifiable dans un lecteur PDF)."""
    texte, cases = valeurs(r)
    lecteur = PdfReader(str(CERFA))
    sortie = PdfWriter(clone_from=lecteur)
    cochees = {c: NameObject('/Oui') for c in cases}
    for page in sortie.pages:
        sortie.update_page_form_field_values(page, {**texte, **cochees}, auto_regenerate=False)
    sortie.set_need_appearances_writer(True)
    buf = io.BytesIO()
    sortie.write(buf)
    return buf.getvalue()
