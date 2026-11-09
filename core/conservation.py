# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/conservation.py
"""Durées de conservation (RGPD), traitement par traitement.

Le délégué à la protection des données (DPO) remplit le modèle CSV (Administration → Durées de conservation →
« Télécharger le modèle »), l'administrateur l'importe. Toutes les durées sont en mois.

Ordre de priorité d'une durée : la valeur importée ; à défaut l'ancienne clé de configuration (ex.
RGPD_ARCHIVAGE_ANS) ; à défaut la valeur par défaut de CID. Les traitements marqués « appliqué » sont purgés ou
proposés à l'archivage par CID lui-même ; les autres sont documentés ici en attendant."""
import csv
import io
import re
import unicodedata

# code, traitement, données, base active par défaut (mois), archivage intermédiaire par défaut (mois),
# point de départ actuel, appliqué automatiquement par CID ?
SUIT = "dernière activité du dossier usager (archivage, puis effacement)"
TRAITEMENTS = [
    ("USAGER_DOSSIER", "Dossier usager", "Identité, coordonnées, famille, MDS de rattachement, référent",
     36, 12, "dernière activité du dossier (archivage, puis effacement)", True),
    ("USAGER_JOURNAL", "Journal d'accompagnement", "Entretiens, observations, suites à donner", 36, 12, SUIT, True),
    ("USAGER_BUDGET", "Budget du foyer", "Ressources, charges, dettes", 36, 12, SUIT, True),
    ("GED_DOCUMENTS", "Documents de l'usager (GED)", "Pièces justificatives, courriers, rapports", 36, 12, SUIT, True),
    ("PLANNING_RDV", "Rendez-vous", "Date, agent, usager, issue du rendez-vous", 36, 12, SUIT, True),
    ("MESSAGERIE", "Messagerie interne", "Messages entre agents (peuvent citer un usager)", None, None,
     "pas de durée propre", False),
    ("ATELIERS", "Ateliers collectifs", "Inscriptions, présences", 36, 12, SUIT, True),
    ("AFASE", "Aides financières (AFASE)", "Demande, évaluation, décision, paiement, recours", 36, 12, SUIT, True),
    ("CAP", "Chèques service (CAP)", "Demande, décision, remise, feuille signée", 36, 12, SUIT, True),
    ("REGIE_URGENCE", "Régie d'urgence", "Demande, décision, versement", 36, 12, SUIT, True),
    ("IP", "Informations préoccupantes", "IP, évaluation, rapports, visas, saisine du procureur", 36, 12, SUIT, True),
    ("RSA_CONTRATS", "RSA : contrats, prescriptions, réorientations", "Contrats, actions prescrites, décisions",
     36, 12, SUIT, True),
    ("RSA_SANTE", "RSA : contrat santé", "Avis du médecin du pôle (jamais le certificat)", 36, 12, SUIT, True),
    ("FSL", "Fonds de solidarité logement", "Demande, avis, visa du cadre, décision", 36, 12, SUIT, True),
    ("LOGEMENT_DEMANDE", "Demande de logement social", "NUD, DALO, mutation, Al'In, souhaits", 36, 12, SUIT, True),
    ("COPP", "Commission des publics prioritaires", "Saisine, motifs, rapport social, décision", 36, 12, SUIT, True),
    ("ASELL", "Orientation ASELL", "Fiche d'orientation, budget, logement, évaluation, réponse de l'opérateur", 36, 12, SUIT, True),
    ("EXPULSION_DOSSIER", "Prévention des expulsions : dossier",
     "Fiche de liaison, fiche CAF, bailleur, dette, audience, décision, étapes", None, None,
     "clôture du dossier", True),
    ("EXPULSION_DSF", "Prévention des expulsions : diagnostic",
     "DSF (Cerfa 16227), bordereau de carence, convocations, questionnaire bailleur", None, None,
     "clôture du dossier", True),
    ("HEBERGEMENT_URGENCE", "Hébergement d'urgence",
     "Démarches (115, SIAO…), fiches de demande, de renouvellement et d'orientation, prise en charge", None, None,
     "clôture du dossier", True),
    ("ANNUAIRE_RECHERCHES", "Annuaire des usagers : recherches", "Qui a cherché quoi (critères, codes trouvés)",
     12, None, "date de la recherche", True),
    ("JOURNAL_ACTIVITE", "Journal d'activité (traçabilité)", "Consultations, modifications, connexions des agents",
     12, None, "date de l'action", True),
    ("CONNECTEURS_API", "Appels aux services de l'État (CAF, impôts, France Travail)", "Journal des appels et réponses",
     None, None, "pas de durée propre", False),
    ("COMPTES_AGENTS", "Comptes des agents", "Identité, profils, MDS, fonction", None, None,
     "pas de durée propre (compte désactivé au départ)", False),
    ("SIGNATURES_AGENTS", "Signatures numérisées des cadres", "Image de la signature", None, None,
     "pas de durée propre", False),
]
PAR_CODE = {t[0]: t for t in TRAITEMENTS}

SORTS = [("SUPPRESSION", "Suppression"), ("ANONYMISATION", "Anonymisation"),
         ("ARCHIVES", "Versement aux archives départementales")]

COLONNES = ["code", "traitement", "donnees_concernees", "actuel_base_active (en mois)",
            "actuel_archivage_intermediaire (en mois)", "actuel_point_de_depart", "duree_base_active (en mois)",
            "point_de_depart", "duree_archivage_intermediaire (en mois)", "sort_final", "base_legale_ou_reference",
            "commentaire_dpo"]


def _regle(code):
    from core.models import DureeConservation
    return DureeConservation.objects.filter(code=code).first()


def mois(code, quoi='base', cle_ancienne=None, facteur=1):
    """Durée en mois d'un traitement : 'base' (base active) ou 'archivage' (archivage intermédiaire)."""
    r = _regle(code)
    v = (r.base_active_mois if quoi == 'base' else r.archivage_mois) if r else None
    if v is not None:
        return v
    if cle_ancienne:
        from core.models import Configuration
        c = Configuration.objects.filter(cle=cle_ancienne).first()
        try:
            if c and c.valeur not in (None, ""):
                return int(c.valeur) * facteur
        except ValueError:
            pass
    t = PAR_CODE[code]
    return t[3] if quoi == 'base' else t[4]


def sort_final(code):
    r = _regle(code)
    return r.sort_final if r else ""


# ------------------------------------------------------------------------------------------------- CSV
def modele_csv():
    """Le modèle à remplir, avec les réglages en vigueur (valeurs importées comprises)."""
    out = io.StringIO()
    w = csv.writer(out, delimiter=';')
    w.writerow(COLONNES)
    for code, t, dn, base, arch, depart, _ in TRAITEMENTS:
        r = _regle(code)
        w.writerow([code, t, dn, "" if base is None else base, "" if arch is None else arch, depart,
                    "" if not r or r.base_active_mois is None else r.base_active_mois, r.point_de_depart if r else "",
                    "" if not r or r.archivage_mois is None else r.archivage_mois,
                    dict(SORTS).get(r.sort_final, "") if r else "", r.reference if r else "",
                    r.commentaire if r else ""])
    return "﻿" + out.getvalue()


def _norme(t):
    t = "".join(c for c in unicodedata.normalize("NFD", str(t or "")) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z]", "", t.lower())


def _colonne(entetes, debut):
    for i, e in enumerate(entetes):
        if _norme(e).startswith(_norme(debut)):
            return i
    return None


def _mois(texte):
    texte = (texte or "").strip()
    if not texte:
        return None, None
    if not re.fullmatch(r"\d{1,3}", texte):
        return None, f"« {texte} » n'est pas un nombre entier de mois"
    return int(texte), None


def _sort(texte):
    n = _norme(texte)
    if not n:
        return "", None
    for code, lib in SORTS:
        if n.startswith(_norme(code)[:6]) or _norme(lib).startswith(n) or n.startswith(_norme(lib)[:8]):
            return code, None
    if "archiv" in n or "verse" in n:
        return "ARCHIVES", None
    return None, f"sort final « {texte} » inconnu (suppression, anonymisation ou versement aux archives)"


def lire_csv(contenu):
    """Analyse le fichier rempli par le DPO. Renvoie (lignes valides, erreurs) ; rien n'est enregistré ici.
    Une seule erreur bloque tout l'import (on ne garde pas un import à moitié)."""
    if isinstance(contenu, bytes):
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                contenu = contenu.decode(enc)
                break
            except UnicodeDecodeError:
                continue
    delim = ';' if contenu.count(';') >= contenu.count(',') else ','
    lignes = list(csv.reader(io.StringIO(contenu), delimiter=delim))
    if not lignes:
        return [], ["Fichier vide."]
    ent = lignes[0]
    idx = {k: _colonne(ent, v) for k, v in [('code', 'code'), ('base', 'duree_base_active'),
                                            ('depart', 'point_de_depart'), ('arch', 'duree_archivage'),
                                            ('sort', 'sort_final'), ('ref', 'base_legale'), ('com', 'commentaire')]}
    if idx['code'] is None or idx['base'] is None:
        return [], ["Colonnes « code » et « duree_base_active (en mois) » introuvables : partez du modèle de CID."]
    valides, erreurs, vus = [], [], set()
    for n, l in enumerate(lignes[1:], start=2):
        if not any(c.strip() for c in l):
            continue
        val = lambda k: (l[idx[k]].strip() if idx[k] is not None and idx[k] < len(l) else "")   # noqa: E731
        code = val('code').upper()
        if code not in PAR_CODE:
            erreurs.append(f"Ligne {n} : code « {code} » inconnu (ne modifiez pas la colonne code).")
            continue
        if code in vus:
            erreurs.append(f"Ligne {n} : {code} figure deux fois.")
            continue
        vus.add(code)
        base, e1 = _mois(val('base'))
        arch, e2 = _mois(val('arch'))
        sort, e3 = _sort(val('sort'))
        probs = [e for e in (e1, e2, e3) if e]
        if probs:
            erreurs.append(f"Ligne {n} ({code}) : " + " ; ".join(probs) + ".")
            continue
        if base is None and arch is None and not sort and not val('ref') and not val('com') and not val('depart'):
            continue                                       # ligne non remplie : CID garde son réglage
        valides.append({'code': code, 'base_active_mois': base, 'archivage_mois': arch,
                        'point_de_depart': val('depart')[:200], 'sort_final': sort or "",
                        'reference': val('ref')[:500], 'commentaire': val('com')[:1000]})
    return valides, erreurs


def importer(contenu, user):
    from core.models import DureeConservation
    valides, erreurs = lire_csv(contenu)
    if erreurs:
        return 0, erreurs
    for v in valides:
        DureeConservation.objects.update_or_create(code=v['code'], defaults=dict(v, importe_par=user))
    return len(valides), []
