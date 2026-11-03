# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/courriers/rendu.py
"""
Rendu d'un modèle de courrier (texte saisi en administration) en paragraphes pour les PDF.

Syntaxe, pensée pour être écrite sans connaissance technique :
  {nom}                         valeur d'une variable du dossier (ex. {date_rdv}, {montant_mensuel}) ;
  {si_condition:texte A|texte B} texte A si la condition est vraie, sinon texte B (« |texte B » facultatif) ;
                                 les deux textes peuvent contenir des variables ;
  **texte**                     en gras ;
  [petit]texte[/petit]          en petits caractères ;
  ligne vide                    nouveau paragraphe ; un simple retour à la ligne reste dans le paragraphe.
Un paragraphe disparaît s'il est vide, ou si toutes ses variables sont vides (ex. une mention facultative
« Voies de recours : {voies_recours} » quand le texte des voies de recours n'est pas renseigné).
Le texte saisi et les valeurs sont échappés : rien de ce qui est tapé ne peut casser le PDF.
"""
import re
from xml.sax.saxutils import escape

VARIABLE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
GRAS = re.compile(r"\*\*(.+?)\*\*", re.S)
PETIT = re.compile(r"\[petit\](.+?)\[/petit\]", re.S)


class ErreurModele(ValueError):
    pass


def _conditions(texte, conditions, erreurs):
    """Remplace chaque {si_x:A|B} (non imbriqués) par A ou B. Les variables à l'intérieur restent à remplacer."""
    sortie, i = [], 0
    while True:
        debut = texte.find("{si_", i)
        if debut < 0:
            sortie.append(texte[i:])
            return "".join(sortie)
        sortie.append(texte[i:debut])
        deux_points = texte.find(":", debut)
        profondeur, j = 0, debut
        while j < len(texte):          # accolade fermante correspondante (les {variables} internes sont permises)
            if texte[j] == "{":
                profondeur += 1
            elif texte[j] == "}":
                profondeur -= 1
                if profondeur == 0:
                    break
            j += 1
        if deux_points < 0 or j >= len(texte) or deux_points > j:
            erreurs.append(f"condition mal écrite près de « {texte[debut:debut + 30]} » (forme : {{si_nom:texte|autre texte}})")
            sortie.append(texte[debut:])
            return "".join(sortie)
        nom = texte[debut + 1:deux_points]
        contenu = texte[deux_points + 1:j]
        if "{si_" in contenu:
            erreurs.append(f"condition {{{nom}:…}} : une condition ne peut pas en contenir une autre")
        si_vrai, _, si_faux = contenu.partition("|")
        if nom not in conditions:
            erreurs.append(f"condition inconnue : {{{nom}:…}}")
            sortie.append(si_faux)
        else:
            sortie.append(si_vrai if conditions[nom] else si_faux)
        i = j + 1


def _valeur(v):
    return escape("" if v is None else str(v)).replace("\n", "<br/>")


def verifier(texte, variables, conditions):
    """Liste des erreurs d'un modèle (variables ou conditions inconnues, syntaxe)."""
    erreurs = []
    tout_vrai = _conditions(texte or "", {c: True for c in conditions}, erreurs)
    tout_faux = _conditions(texte or "", {c: False for c in conditions}, [])
    for t in (tout_vrai, tout_faux):
        for nom in VARIABLE.findall(t):
            if nom not in variables and f"variable inconnue : {{{nom}}}" not in erreurs:
                erreurs.append(f"variable inconnue : {{{nom}}}")
    return erreurs


def paragraphes(texte, valeurs, conditions=None):
    """Texte du modèle → liste de paragraphes au format des PDF (gras, petits caractères, retours à la ligne)."""
    erreurs = []
    texte = _conditions((texte or "").replace("\r\n", "\n"), conditions or {}, erreurs)
    resultat = []
    for bloc in re.split(r"\n[ \t]*\n", texte):
        noms = VARIABLE.findall(bloc)
        if noms and all(str(valeurs.get(n) or "").strip() == "" for n in noms if n in valeurs) \
                and all(n in valeurs for n in noms):
            continue                     # mention facultative dont les données sont vides
        morceaux, fin = [], 0
        for m in VARIABLE.finditer(bloc):
            morceaux.append(escape(bloc[fin:m.start()]))
            morceaux.append(_valeur(valeurs[m.group(1)]) if m.group(1) in valeurs else escape(m.group(0)))
            fin = m.end()
        morceaux.append(escape(bloc[fin:]))
        p = "".join(morceaux).strip().replace("\n", "<br/>")
        p = PETIT.sub(r"<font size=8>\1</font>", GRAS.sub(r"<b>\1</b>", p))
        if p:
            resultat.append(p)
    return resultat


def ligne(texte, valeurs, conditions=None):
    """Texte court sur une ligne (objet du courrier) ; les paragraphes éventuels sont réunis."""
    return " ".join(paragraphes(texte, valeurs, conditions))


def bloc(texte, valeurs, conditions=None):
    """Texte en un seul paragraphe (signature) : les paragraphes sont séparés par une ligne blanche."""
    return "<br/><br/>".join(paragraphes(texte, valeurs, conditions))
