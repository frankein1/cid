# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/services/csv_actions.py
"""
Import et export CSV du référentiel des actions d'insertion.

Format : séparateur « ; », UTF-8 (avec BOM, pour Excel), une ligne d'en-tête (COLONNES). La clé d'une action est
son code, plus le code de sa MDS pour une action locale : une ligne dont la clé existe déjà met l'action à jour.
L'import se fait en deux temps : analyse (aperçu des créations, mises à jour et erreurs), puis enregistrement.
Chaque ligne est contrôlée avec les droits de la personne qui importe (insertion/acces.py).
"""
import csv
import io

from django.db import transaction

COLONNES = ["code", "libelle", "type", "niveau", "mds", "poles", "territoire", "porteur", "public_vise", "duree",
            "destinataires", "pieces_a_joindre", "comite_suivi", "rythme_comite", "aussi_logement", "actif",
            "description"]
AIDE = {
    "code": "obligatoire, propre à CID (ex. ACCGLO)",
    "libelle": "obligatoire",
    "type": "code du type d'action (liste dans CID)",
    "niveau": "DEPARTEMENTAL ou LOCAL",
    "mds": "code de la MDS (actions locales seulement)",
    "poles": "codes des pôles séparés par des virgules ; vide = tout le département",
    "destinataires": "adresses séparées par des virgules",
    "pieces_a_joindre": "pièces séparées par des virgules",
    "comite_suivi": "oui / non", "aussi_logement": "oui / non", "actif": "oui / non (vide = oui)",
}
VRAI = {"oui", "o", "x", "1", "vrai", "true", "yes"}
FAUX = {"non", "n", "0", "faux", "false", "no", ""}


def _liste(valeur):
    return [v.strip() for v in (valeur or "").replace("\n", ",").split(",") if v.strip()]


def _bool(valeur, defaut=False):
    v = (valeur or "").strip().lower()
    if v == "":
        return defaut
    if v in VRAI:
        return True
    if v in FAUX:
        return False
    raise ValueError(f"« {valeur} » : écrire oui ou non")


def modele_csv(types):
    """Fichier modèle : en-tête, ligne d'aide, exemple fictif."""
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=";")
    w.writerow(COLONNES)
    w.writerow(["# " + AIDE.get(c, "") for c in COLONNES])
    exemple_type = types[0].code if types else ""
    w.writerow(["EXEMPLE", "Action d'exemple (à supprimer)", exemple_type, "DEPARTEMENTAL", "", "", "", "Association exemple",
                "Bénéficiaires du RSA", "6 mois", "contact@exemple.org", "Attestation CAF de moins d'un mois",
                "oui", "semestriel", "non", "oui", "Ligne d'exemple : elle est ignorée tant que son code est EXEMPLE."])
    return "﻿" + sortie.getvalue()


def export_csv(actions):
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=";")
    w.writerow(COLONNES)
    for a in actions:
        w.writerow([a.code, a.libelle, a.type_action.code, a.niveau, a.mds.code_mds if a.mds_id else "",
                    ",".join(p.code for p in a.poles.all()), a.territoire, a.porteur, a.public_vise, a.duree,
                    ",".join(a.liste_destinataires), ",".join(a.liste_pieces), "oui" if a.comite_suivi else "non",
                    a.rythme_comite, "oui" if a.aussi_logement else "non", "oui" if a.actif else "non", a.description])
    return "﻿" + sortie.getvalue()


def _lire(texte):
    texte = texte.lstrip("﻿")
    try:
        dialecte = csv.Sniffer().sniff(texte.splitlines()[0], delimiters=";,\t")
    except (csv.Error, IndexError):
        class dialecte(csv.excel):
            delimiter = ";"
    lecteur = csv.DictReader(io.StringIO(texte), dialect=dialecte)
    if not lecteur.fieldnames:
        raise ValueError("fichier vide")
    entetes = [(h or "").strip().lower() for h in lecteur.fieldnames]
    manquantes = [c for c in ("code", "libelle", "type", "niveau") if c not in entetes]
    if manquantes:
        raise ValueError("colonnes manquantes : " + ", ".join(manquantes) + " (téléchargez le fichier modèle)")
    lecteur.fieldnames = entetes
    return lecteur


def analyser(texte, user):
    """Liste de lignes {numero, code, libelle, operation: creation|mise_a_jour|ignoree|erreur, erreurs, donnees}."""
    from mds.models import MDS
    from insertion import acces
    from insertion.models import ActionInsertion, PoleInsertion, TypeActionInsertion
    types = {t.code.lower(): t for t in TypeActionInsertion.objects.all()}
    types.update({t.libelle.lower(): t for t in TypeActionInsertion.objects.all()})
    poles = {p.code.lower(): p for p in PoleInsertion.objects.all()}
    mds_codes = {m.code_mds.lower(): m for m in MDS.objects.all()}
    gerables = set(acces.mds_gerables(user).values_list("pk", flat=True))
    resultat, vues = [], set()
    for numero, ligne in enumerate(_lire(texte), start=2):
        ligne = {k: (v or "").strip() for k, v in ligne.items() if k}
        code = ligne.get("code", "")
        if not any(ligne.values()) or code.startswith("#") or code.upper() == "EXEMPLE":
            continue
        erreurs = []
        niveau = ligne.get("niveau", "").upper().replace("É", "E")
        niveau = {"DEPARTEMENTALE": "DEPARTEMENTAL", "LOCALE": "LOCAL"}.get(niveau, niveau)
        mds = mds_codes.get(ligne.get("mds", "").lower())
        if not code:
            erreurs.append("code manquant")
        if not ligne.get("libelle"):
            erreurs.append("libellé manquant")
        type_action = types.get(ligne.get("type", "").lower())
        if not type_action:
            erreurs.append(f"type inconnu : « {ligne.get('type', '')} »")
        if niveau not in (ActionInsertion.DEPARTEMENTAL, ActionInsertion.LOCAL):
            erreurs.append("niveau : DEPARTEMENTAL ou LOCAL")
        elif niveau == ActionInsertion.LOCAL:
            if not mds:
                erreurs.append(f"MDS inconnue : « {ligne.get('mds', '')} »")
            elif mds.pk not in gerables:
                erreurs.append(f"vous ne pouvez pas gérer les actions locales de {mds.code_mds}")
        else:
            mds = None
            if not acces.peut_gerer_departemental(user):
                erreurs.append("vous ne pouvez pas gérer les actions départementales")
        poles_ligne = []
        for c in _liste(ligne.get("poles")):
            if c.lower() in poles:
                poles_ligne.append(poles[c.lower()])
            else:
                erreurs.append(f"pôle inconnu : « {c} »")
        booleens = {}
        for champ, defaut in (("comite_suivi", False), ("aussi_logement", False), ("actif", True)):
            try:
                booleens[champ] = _bool(ligne.get(champ), defaut)
            except ValueError as e:
                erreurs.append(f"{champ} {e}")
        cle = (code.lower(), mds.pk if mds else None)
        if cle in vues:
            erreurs.append("code en double dans le fichier")
        vues.add(cle)
        existante = ActionInsertion.objects.filter(code=code, mds=mds).first() if code and not erreurs else None
        resultat.append({
            "numero": numero, "code": code, "libelle": ligne.get("libelle", ""), "erreurs": erreurs,
            "operation": "erreur" if erreurs else ("mise_a_jour" if existante else "creation"),
            "donnees": None if erreurs else {
                "code": code, "libelle": ligne["libelle"][:200], "type_action_id": type_action.pk, "niveau": niveau,
                "mds_id": mds.pk if mds else None, "poles": [p.pk for p in poles_ligne],
                "territoire": ligne.get("territoire", "")[:255], "porteur": ligne.get("porteur", "")[:200],
                "public_vise": ligne.get("public_vise", ""), "duree": ligne.get("duree", "")[:100],
                "destinataires": "\n".join(_liste(ligne.get("destinataires"))),
                "pieces_a_joindre": "\n".join(_liste(ligne.get("pieces_a_joindre"))),
                "rythme_comite": ligne.get("rythme_comite", "")[:100], "description": ligne.get("description", ""),
                **booleens},
        })
    return resultat


@transaction.atomic
def enregistrer(lignes, user):
    """Applique les lignes valides d'une analyse. Renvoie (créées, mises à jour)."""
    from insertion.models import ActionInsertion
    crees = maj = 0
    for l in lignes:
        d = l.get("donnees")
        if not d:
            continue
        poles = d.pop("poles")
        action, cree = ActionInsertion.objects.update_or_create(
            code=d["code"], mds_id=d["mds_id"], defaults={**d, "modifie_par": user})
        action.poles.set(poles)
        crees += cree
        maj += not cree
    return crees, maj
