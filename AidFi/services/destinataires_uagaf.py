# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/services/destinataires_uagaf.py
"""Adresses mail de l'UAGAF pour l'envoi des AFASE : saisies ou importées par CSV dans l'administration,
jamais écrites dans le code."""
import csv
import io

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

COLONNES_DESTINATAIRES = ('nom', 'email', 'actif')
VRAI = {'', 'oui', 'o', 'yes', 'y', '1', 'vrai', 'true'}
FAUX = {'non', 'n', 'no', '0', 'faux', 'false'}


def importer_destinataires(texte):
    """Importe les destinataires depuis le texte d'un CSV (séparateur « ; », en-tête nom;email;actif). Une adresse
    déjà connue est mise à jour, une nouvelle créée ; les autres ne sont pas supprimées. Retourne (créés, mis à jour).
    Lève ValueError avec un message lisible si le fichier est invalide (rien n'est alors enregistré)."""
    from AidFi.models import DestinataireUAGAF
    lignes = list(csv.DictReader(io.StringIO(texte), delimiter=';'))
    if not lignes or any(c not in lignes[0] for c in COLONNES_DESTINATAIRES):
        raise ValueError("En-tête attendu : " + ";".join(COLONNES_DESTINATAIRES))
    valides = []
    for n, ligne in enumerate(lignes, start=2):
        email = (ligne['email'] or '').strip()
        actif = (ligne['actif'] or '').strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError(f"Ligne {n} invalide : adresse mail incorrecte ({email or 'vide'}).")
        if actif not in VRAI | FAUX:
            raise ValueError(f"Ligne {n} invalide : la colonne actif doit valoir oui ou non.")
        valides.append((email, (ligne['nom'] or '').strip(), actif not in FAUX))
    crees = maj = 0
    for email, nom, actif in valides:
        _, cree = DestinataireUAGAF.objects.update_or_create(email=email, defaults={'nom': nom, 'actif': actif})
        crees, maj = crees + cree, maj + (not cree)
    return crees, maj


def adresses_actives():
    """Adresses des destinataires actifs de l'UAGAF (liste vide si aucune n'est saisie)."""
    from AidFi.models import DestinataireUAGAF
    return list(DestinataireUAGAF.objects.filter(actif=True).values_list('email', flat=True))
