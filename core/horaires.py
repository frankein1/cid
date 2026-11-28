# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/horaires.py
"""Saisie des heures et dates en 24 h, quel que soit l'appareil (pas de sélecteur natif 12 h / 24 h).
Les rendez-vous se saisissent par pas de 10 minutes."""
import re
from datetime import date, datetime, time

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

PATTERN_HEURE = r"([01]\d|2[0-3]):[0-5]\d"
PATTERN_DATE_HEURE = r"\d{2}/\d{2}/\d{4} " + PATTERN_HEURE
MESSAGE_PAS_DE_DIX = "Les horaires se saisissent par pas de 10 minutes (00, 10, 20, 30, 40 ou 50)."


class TexteHoraire(forms.TimeInput):
    """Heure HH:MM en 24 h, saisie texte (pas de sélecteur natif)."""
    input_type = 'text'

    def __init__(self, attrs=None, format=None):
        base = {'placeholder': 'HH:MM', 'pattern': PATTERN_HEURE, 'maxlength': '5', 'inputmode': 'numeric',
                'autocomplete': 'off'}
        super().__init__(attrs={**base, **(attrs or {})}, format='%H:%M')


class TexteDateHeure(forms.DateTimeInput):
    """Date et heure JJ/MM/AAAA HH:MM en 24 h, saisie texte."""
    input_type = 'text'

    def __init__(self, attrs=None, format=None):
        base = {'placeholder': 'JJ/MM/AAAA HH:MM', 'pattern': PATTERN_DATE_HEURE, 'maxlength': '16',
                'inputmode': 'numeric', 'autocomplete': 'off'}
        super().__init__(attrs={**base, **(attrs or {})}, format='%d/%m/%Y %H:%M')


def lire_heure(texte):
    """Heure saisie (HH:MM) -> time, ou None si vide ou invalide."""
    texte = (texte or '').strip()
    if not re.fullmatch(PATTERN_HEURE, texte):
        return None
    return datetime.strptime(texte, '%H:%M').time()


def lire_date_heure(texte):
    """Date et heure saisies (JJ/MM/AAAA HH:MM, ou format ISO des anciens liens) -> datetime aware (heure de Paris)."""
    texte = (texte or '').strip()
    for fmt in ('%d/%m/%Y %H:%M', '%Y-%m-%dT%H:%M'):
        try:
            naive = datetime.strptime(texte, fmt)
        except ValueError:
            continue
        return timezone.make_aware(naive) if timezone.is_naive(naive) else naive
    return None


def lire_jour(texte):
    """Date ISO (AAAA-MM-JJ, type date du navigateur) -> date, ou None."""
    try:
        return date.fromisoformat((texte or '').strip())
    except ValueError:
        return None


def verifier_pas_de_dix(heure):
    if heure is not None and heure.minute % 10:
        raise ValidationError(MESSAGE_PAS_DE_DIX)
    return heure


def verifier_pas_de_dix_date_heure(moment):
    if moment is not None and moment.minute % 10:
        raise ValidationError(MESSAGE_PAS_DE_DIX)
    return moment
