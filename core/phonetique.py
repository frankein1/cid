# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/phonetique.py
"""Clé phonétique simplifiée pour le français : deux orthographes qui se prononcent pareil donnent la même clé.
Frederik, Frédéric, Frederick, Frédérique → « FREDERIK » ; Mickaël, Michaël, Mikael → « MIKAEL ».

Elle sert à proposer des « orthographes proches » quand on cherche un usager. Ce n'est pas une identification :
l'agent vérifie toujours la date de naissance. Les clés sont enregistrées sur l'usager (champs indexés), la
recherche reste donc rapide quelle que soit la taille de la base."""
import re
import unicodedata

# Remplacements appliqués dans l'ordre (du plus long au plus court)
_REGLES = [
    (r"ph", "f"), (r"sch", "ch"), (r"ch(?=[lr])", "k"), (r"^chae", "kae"), (r"(?<=i)chae", "kae"), (r"qu", "k"), (r"q", "k"), (r"ck", "k"), (r"cc(?=[eiy])", "ks"), (r"cc", "k"),
    (r"c(?=[eiy])", "s"), (r"ch", "§"), (r"c", "k"), (r"gu(?=[eiy])", "g"), (r"g(?=[eiy])", "j"),
    (r"ge(?=[aou])", "j"), (r"th", "t"), (r"h", ""), (r"§", "ch"), (r"w", "v"), (r"y", "i"), (r"z", "s"),
    (r"x", "ks"), (r"eau", "o"), (r"au", "o"), (r"ai|ei", "e"), (r"(?<=[aeiou])s(?=[aeiou])", "z"),
    (r"[ae][nm](?=[^aeiou]|$)", "an"), (r"(ai|ei|i|u)[nm](?=[^aeiou]|$)", "in"),
]


def sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte or "") if unicodedata.category(c) != "Mn")


def cle(texte):
    """Clé phonétique d'un nom ou d'un prénom (les mots composés sont accolés : « Jean-Pierre » → « JEANPIER »)."""
    s = re.sub(r"[^a-z]", "", sans_accents(texte).lower().replace("œ", "oe").replace("æ", "ae"))
    if not s:
        return ""
    s = re.sub(r"(.)\1+", r"\1", s)                 # lettres doublées
    for motif, rempl in _REGLES:
        s = re.sub(motif, rempl, s)
    s = re.sub(r"(.)\1+", r"\1", s)
    s = re.sub(r"ier$", "i", s)                      # Garnier, Garnié
    s = re.sub(r"(e|es|s|t|ts|d|ds|x)$", "", s) or s  # finales muettes
    s = re.sub(r"(.)\1+", r"\1", s)
    return s.upper()[:40]


def chiffres(telephone):
    """Numéro de téléphone réduit à ses 9 derniers chiffres (+33 6…, 06 …, 06.…, 0033… se comparent)."""
    d = re.sub(r"\D", "", telephone or "")
    return d[-9:] if len(d) >= 9 else d
