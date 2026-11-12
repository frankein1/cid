# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/signature.py
"""Utilitaires communs pour afficher une validation nominative dans CID."""


def initiales_utilisateur(user):
    """Retourne jusqu'à deux initiales stables à partir du prénom et du nom."""
    if not user:
        return ""
    prenom = (getattr(user, "first_name", "") or "").strip()
    nom = (getattr(user, "last_name", "") or "").strip()
    initiales = "".join(part[0] for part in (prenom, nom) if part)
    if not initiales:
        identifiant = (getattr(user, "username", "") or "").strip()
        initiales = identifiant[:2]
    return initiales.upper()[:8]


def libelle_signature(user):
    """Affiche une signature d'agent lisible, selon le modèle AFASE : initiale + nom."""
    if not user:
        return "Non renseigné"
    prenom = (getattr(user, "first_name", "") or "").strip()
    nom = (getattr(user, "last_name", "") or "").strip()
    if not nom:
        return (getattr(user, "username", "") or "").strip() or "Non renseigné"
    initiale = f"{prenom[0].upper()}." if prenom else ""
    return " ".join(part for part in (initiale, nom) if part)
