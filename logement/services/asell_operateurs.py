# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/asell_operateurs.py
"""Liste des opérateurs conventionnés (accompagnement social lié au FSL) : import du tableau annuel du Département
(CSV ou Excel, mêmes colonnes que la liste diffusée) et choix de l'opérateur selon la commune de l'usager.

Colonnes reconnues (l'ordre importe peu ; les lignes de titre au-dessus du tableau sont ignorées) :
  Sigle opérateurs ; Nom opérateurs ; Adresse ; Code postal et ville ; Téléphone ; Adresses mail ; Territoires ;
  Nature ; Thématique ; Complément thématique
Les cellules fusionnées du tableau arrivent vides sur les lignes suivantes : une ligne sans sigle reprend l'opérateur
de la ligne du dessus (signalée dans les avertissements). L'import est tout ou rien ; il désactive la liste précédente
sans l'effacer."""
import csv
import io
import re

from django.db import transaction

from logement.models import OperateurASELL as O

COLONNES = [('sigle', "Sigle opérateurs"), ('nom', "Nom opérateurs"), ('adresse', "Adresse"),
            ('cp_ville', "Code postal et ville"), ('telephone', "Téléphone"), ('emails', "Adresses mail"),
            ('territoire', "Territoires"), ('nature', "Nature"), ('thematique', "Thématique"),
            ('complement', "Complément thématique")]
OBLIGATOIRES = ('sigle', 'territoire', 'nature', 'thematique')
# reprises de la ligne du dessus quand la cellule est vide (cellules fusionnées du tableau)
REPRISES = ['sigle', 'nom', 'adresse', 'cp_ville', 'telephone', 'emails', 'nature']


def norme(texte):
    from mds.models import MDS
    return MDS._norme(texte)


# ------------------------------------------------------------------------------------------------- territoires
def _communes(territoire):
    """« Communes de Aubagne, Auriol et La Penne » → {AUBAGNE, AURIOL, LA PENNE}."""
    out = set()
    for m in re.split(r"[,;:\n]|\s+et\s+|\s+&\s+", territoire or "", flags=re.I):
        n = re.sub(r"^(COMMUNES?|VILLE|SECTEUR) (DE |D |DU |DES )?", "", norme(m))
        if len(n) >= 4:
            out.add(n)
    return out


def _arrondissements(territoire):
    """« 1er, 2ème, 3ème et 15ème arrondissements de Marseille » → {1, 2, 3, 15} (normé : 1ER, 2EME…)."""
    t = norme(territoire)
    return {int(n) for n in re.findall(r"\b(\d{1,2})(?:ER|EME|E)\b", t)} if "ARRONDISSEMENT" in t else set()


def couvre(op, code_postal, ville):
    """La ligne de la liste couvre-t-elle cette adresse ?
    « Département » : partout ; Marseille : par arrondissement quand la liste les précise, sinon toute la ville ;
    ailleurs : par commune. Une résidence sociale (public d'un lieu) ne se rattache à aucune commune : elle reste dans
    « autres opérateurs »."""
    t = norme(op.territoire)
    if not t or t.startswith("RESIDENCE"):
        return False
    if "DEPARTEMENT" in t:
        return True
    cp, v = (code_postal or "").strip(), norme(ville)
    marseille_cp = re.fullmatch(r"130(0[1-9]|1[0-6])", cp)
    if marseille_cp or v == "MARSEILLE":
        if "MARSEILLE" not in t:
            return False
        arr = _arrondissements(op.territoire)
        return not arr or not marseille_cp or int(cp[-2:]) in arr
    return bool(v) and v in _communes(op.territoire)


def pour_usager(type_mesure, b):
    """(opérateurs du secteur de l'usager, autres opérateurs) pour la mesure demandée ; publics spécifiques en fin."""
    qs = list(O.objects.filter(actif=True, nature=O.ASELL, thematique=type_mesure).order_by('sigle', 'pk'))
    secteur = [o for o in qs if couvre(o, b.code_postal, b.ville)]
    autres = [o for o in qs if o not in secteur]
    cle = lambda o: (bool(o.public_specifique), o.sigle)          # noqa: E731
    return sorted(secteur, key=cle), sorted(autres, key=cle)


# ------------------------------------------------------------------------------------------------- import
def _texte(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return re.sub(r"\s+", " ", str(v)).strip()


def _lignes(contenu, nom_fichier):
    if (nom_fichier or "").lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        ws = load_workbook(io.BytesIO(contenu), read_only=True, data_only=True).worksheets[0]
        return [[_texte(c) for c in r] for r in ws.iter_rows(values_only=True)]
    texte = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texte = contenu.decode(enc) if isinstance(contenu, bytes) else contenu
            break
        except UnicodeDecodeError:
            continue
    delim = ';' if texte.count(';') >= texte.count(',') else ','
    return [[_texte(c) for c in r] for r in csv.reader(io.StringIO(texte), delimiter=delim)]


def _entetes(ligne):
    n = [norme(c) for c in ligne]

    def cherche(pred):
        return next((i for i, c in enumerate(n) if c and pred(c)), None)
    return {'sigle': cherche(lambda c: c.startswith("SIGLE")), 'nom': cherche(lambda c: c.startswith("NOM")),
            'adresse': cherche(lambda c: c.startswith("ADRESSE") and "MAIL" not in c),
            'cp_ville': cherche(lambda c: "CODE POSTAL" in c), 'telephone': cherche(lambda c: c.startswith("TELEPHONE")),
            'emails': cherche(lambda c: "MAIL" in c), 'territoire': cherche(lambda c: c.startswith("TERRITOIRE")),
            'nature': cherche(lambda c: c.startswith("NATURE")),
            'thematique': cherche(lambda c: c.startswith("THEMATIQUE")),
            'complement': cherche(lambda c: c.startswith("COMPLEMENT"))}


def _thematique(texte):
    t = norme(texte)
    for mot, code in (("GENERALISTE", O.GENERALISTE), ("RENFORCE", O.RENFORCE), ("COURTE", O.COURTE_DUREE),
                      ("ATELIER", O.ATELIERS), ("REHABILITATION", O.AUTO_REHABILITATION)):
        if mot in t:
            return code
    return None


def _public(texte):
    """« à public spécifique Jeunes 18/30 ans » → « Jeunes 18/30 ans »."""
    return re.sub(r"^\s*(a|à)\s+public\s+sp[ée]cifique\s*:?\s*", "", texte or "", flags=re.I).strip()[:255]


def lire(contenu, nom_fichier=""):
    """(lignes valides, année, erreurs, avertissements). Rien n'est enregistré ici."""
    try:
        lignes = _lignes(contenu, nom_fichier)
    except Exception as e:      # noqa: BLE001 – fichier illisible : on le dit, sans planter l'administration
        return [], None, [f"Fichier illisible : {e}"], []
    debut = next((i for i, l in enumerate(lignes) if any(norme(c).startswith("SIGLE") for c in l)
                  and any(norme(c).startswith("TERRITOIRE") for c in l)), None)
    if debut is None:
        return [], None, ["Ligne d'en-têtes introuvable : il faut au moins les colonnes « Sigle opérateurs » et "
                          "« Territoires » (partez du modèle)."], []
    annee = next((int(m) for l in lignes[:debut] for c in l for m in re.findall(r"\b(20\d\d)\b", c)), None) \
        or next((int(m) for m in re.findall(r"(20\d\d)", nom_fichier or "")), None)
    idx = _entetes(lignes[debut])
    manque = [lib for cle, lib in COLONNES if idx[cle] is None and cle in OBLIGATOIRES]
    if manque:
        return [], annee, [f"Colonne(s) introuvable(s) : {', '.join(manque)}."], []
    valides, erreurs, avertissements, herites, prec, terr_ref = [], [], [], [], {}, ""
    for n, l in enumerate(lignes[debut + 1:], start=debut + 2):
        val = {cle: (l[i] if i is not None and i < len(l) else "") for cle, i in idx.items()}
        if norme(val['sigle']).startswith("SIGLE") or not any(val.values()):
            continue                                         # en-tête répété en haut de page, ligne vide
        if not val['thematique'] and not val['nature']:
            continue                                         # titre, pied de page, note
        if val['sigle'] and prec.get('sigle') and val['sigle'] != prec['sigle']:
            prec, terr_ref = {}, ""                          # nouvel opérateur : on ne reprend rien du précédent
        if not val['sigle'] and prec.get('sigle'):
            herites.append(n)
        for cle in REPRISES:
            if not val[cle] and prec.get(cle):
                val[cle] = prec[cle]
        # territoire général de l'opérateur : celui d'une ligne sans complément (une résidence a son propre lieu)
        if not val['territoire']:
            val['territoire'] = terr_ref
        if val['territoire'] and not val['complement']:
            terr_ref = val['territoire']
        prec = val
        thematique, nature = _thematique(val['thematique']), norme(val['nature'])
        if not val['sigle']:
            erreurs.append(f"Ligne {n} : sigle de l'opérateur manquant.")
        elif nature not in dict(O.NATURES):
            erreurs.append(f"Ligne {n} ({val['sigle']}) : nature « {val['nature']} » inconnue (ASELL, ASC ou ALL).")
        elif thematique is None:
            erreurs.append(f"Ligne {n} ({val['sigle']}) : thématique « {val['thematique']} » inconnue.")
        else:
            valides.append(O(sigle=val['sigle'][:60], nom=(val['nom'] or val['sigle'])[:150],
                             adresse=val['adresse'][:255], cp_ville=val['cp_ville'][:100],
                             telephone=val['telephone'][:30],
                             emails=", ".join(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", val['emails']))[:255],
                             nature=nature, thematique=thematique, territoire=val['territoire'],
                             public_specifique=_public(val['complement']), annee=annee))
    if herites:
        avertissements.append(f"{len(herites)} ligne(s) sans sigle, rattachée(s) à l'opérateur de la ligne du dessus "
                              f"(lignes {', '.join(map(str, herites[:30]))}) : vérifiez-les après l'import.")
    if not valides and not erreurs:
        erreurs.append("Aucune ligne d'opérateur dans le fichier.")
    return valides, annee, erreurs, avertissements


def importer(contenu, nom_fichier="", annee=None):
    """Tout ou rien. Renvoie (nombre importé, nombre de lignes de l'ancienne liste désactivées, erreurs, avertissements)."""
    valides, annee_lue, erreurs, avertissements = lire(contenu, nom_fichier)
    if erreurs:
        return 0, 0, erreurs, []
    with transaction.atomic():
        anciens = O.objects.filter(actif=True).update(actif=False)
        for o in valides:
            o.annee = annee or annee_lue
        O.objects.bulk_create(valides)
    return len(valides), anciens, [], avertissements


def modele_csv():
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow([lib for _, lib in COLONNES])
    w.writerow(["EXEMPLE", "ASSOCIATION EXEMPLE (fictif)", "1, rue de l'Exemple", "13000 VILLE", "04 00 00 00 00",
                "contact@example.com", "Commune A, Commune B et Commune C", "ASELL", "Généraliste", ""])
    w.writerow(["", "", "", "", "", "", "", "", "Renforcé", ""])
    return "﻿" + buf.getvalue()
