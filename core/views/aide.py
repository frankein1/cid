# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/views/aide.py
"""
Fiches d'aide de CID (docs/aide/) servies à l'adresse /aide/ : les mêmes fichiers s'ouvrent aussi
directement depuis le dossier. Accès libre (aucune donnée réelle : captures sur données fictives).
"""
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404

DOSSIER = Path(settings.BASE_DIR) / "docs" / "aide"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".md": "text/plain; charset=utf-8",
         ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def aide(request, chemin="index.html"):
    racine = DOSSIER.resolve()
    fichier = (racine / chemin).resolve()
    if not fichier.is_relative_to(racine) or not fichier.is_file() or fichier.suffix.lower() not in TYPES:
        raise Http404("Fiche d'aide introuvable.")
    reponse = FileResponse(open(fichier, "rb"), content_type=TYPES[fichier.suffix.lower()])
    reponse["Cache-Control"] = "public, max-age=3600"
    return reponse
