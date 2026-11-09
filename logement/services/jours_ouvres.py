# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/jours_ouvres.py
"""Jours ouvrés (hors week-end et jours fériés de France métropolitaine) : délais du DSF, exprimés en jours ouvrés
par la note MDS et la notice nationale. Aucune dépendance : les fériés mobiles se calculent à partir de Pâques."""
from datetime import date, timedelta
from functools import lru_cache


@lru_cache(maxsize=None)
def paques(annee):
    """Dimanche de Pâques (algorithme grégorien anonyme)."""
    a, b, c = annee % 19, annee // 100, annee % 100
    d, e = b // 4, b % 4
    f, g = (b + 8) // 25, (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois, jour = (h + l - 7 * m + 114) // 31, ((h + l - 7 * m + 114) % 31) + 1
    return date(annee, mois, jour)


@lru_cache(maxsize=None)
def feries(annee):
    p = paques(annee)
    return frozenset({
        date(annee, 1, 1), p + timedelta(days=1), date(annee, 5, 1), date(annee, 5, 8),
        p + timedelta(days=39), p + timedelta(days=50), date(annee, 7, 14), date(annee, 8, 15),
        date(annee, 11, 1), date(annee, 11, 11), date(annee, 12, 25)})


def ouvre(jour):
    return jour.weekday() < 5 and jour not in feries(jour.year)


def ajouter(jour, n):
    """n jours ouvrés après « jour »."""
    while n > 0:
        jour += timedelta(days=1)
        n -= 1 if ouvre(jour) else 0
    return jour


def retrancher(jour, n):
    """n jours ouvrés avant « jour »."""
    while n > 0:
        jour -= timedelta(days=1)
        n -= 1 if ouvre(jour) else 0
    return jour
