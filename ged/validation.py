# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ged/validation.py
"""Règles de dépôt d'un fichier dans la GED (taille, extension), communes au formulaire GED et à la messagerie."""
import os

# Jamais acceptées, même si un type de document les autorisait par erreur (exécutables, scripts, pages web)
INTERDITES = {"exe", "bat", "cmd", "com", "msi", "scr", "ps1", "vbs", "js", "jar", "sh", "php", "py", "html", "htm",
              "svg", "hta", "dll", "lnk"}


def extensions(type_doc):
    """Extensions autorisées d'un type, normalisées (« .PDF » et « pdf » valent « pdf »)."""
    return [str(e).strip().lower().lstrip(".") for e in (type_doc.extensions_autorisees or []) if str(e).strip()]


def erreurs_fichier(fichier, type_doc):
    """Liste des raisons de refuser ce fichier pour ce type de document (vide = accepté)."""
    nom = getattr(fichier, "name", "") or ""
    ext = os.path.splitext(nom)[1].lower().lstrip(".")
    erreurs = []
    if not getattr(fichier, "size", 0):
        erreurs.append(f"« {nom} » est vide.")
    if fichier.size and type_doc.taille_max_mb and fichier.size > type_doc.taille_max_mb * 1024 * 1024:
        erreurs.append(f"« {nom} » est trop volumineux (maximum {type_doc.taille_max_mb} Mo).")
    autorisees = extensions(type_doc)
    if not ext or ext in INTERDITES or (autorisees and ext not in autorisees):
        erreurs.append(f"« {nom} » : extension {('.' + ext) if ext else '(aucune)'} non autorisée"
                       + (f" (autorisées : {', '.join(autorisees)})." if autorisees else "."))
    return erreurs
