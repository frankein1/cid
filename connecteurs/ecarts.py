# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/ecarts.py
"""Écarts entre la réponse de la CAF / MSA (quotient familial : enfants rattachés, adresse) et la fiche CID.
La réponse n'est PAS enregistrée : on garde seulement une trace « écart signalé le… », que l'agent règle à la main."""
import re
import unicodedata

from django.utils import timezone

from .models import EcartSituation


def _norm(texte):
    t = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", " ", t).strip()


def _enfants_cid(beneficiaire):
    """Dates de naissance des enfants du foyer dans CID (liens « enfant » qui vivent au foyer)."""
    dates = set()
    for m in beneficiaire.reseau_familial():
        if m['type_lien'] == 'ENFANT' and m['vit_au_foyer'] and m['personne'].date_naissance:
            dates.add(m['personne'].date_naissance.isoformat())
    return dates


def _signaler(beneficiaire, nature, detail, user):
    if not EcartSituation.objects.filter(beneficiaire=beneficiaire, nature=nature, regle_le__isnull=True).exists():
        EcartSituation.objects.create(beneficiaire=beneficiaire, source='QUOTIENT_FAMILIAL', nature=nature,
                                      detail=detail[:255], signale_par=user)


def controler_caf(beneficiaire, data, user):
    caf = {e.get('date_naissance') for e in (data.get('enfants') or []) if e.get('date_naissance')}
    cid = _enfants_cid(beneficiaire)
    inconnus, absents = caf - cid, cid - caf
    if inconnus:
        _signaler(beneficiaire, 'ENFANT_INCONNU', f"{len(inconnus)} enfant(s) rattaché(s) à la CAF / MSA, absent(s) "
                  f"du foyer dans CID (année{'s' if len(inconnus) > 1 else ''} de naissance : "
                  f"{', '.join(sorted(d[:4] for d in inconnus))})", user)
    if absents:
        _signaler(beneficiaire, 'ENFANT_NON_DECLARE', f"{len(absents)} enfant(s) du foyer dans CID non rattaché(s) "
                  f"à la CAF / MSA", user)
    adr = data.get('adresse') or {}
    cp_ville = _norm(adr.get('code_postal_ville'))
    voie = _norm(adr.get('numero_libelle_voie'))
    if cp_ville and (beneficiaire.code_postal or '') and not cp_ville.startswith(beneficiaire.code_postal):
        _signaler(beneficiaire, 'ADRESSE', "Commune différente de celle de la fiche", user)
    elif voie and beneficiaire.adresse and voie not in _norm(beneficiaire.adresse) and _norm(beneficiaire.adresse) not in voie:
        _signaler(beneficiaire, 'ADRESSE', "Adresse (voie) différente de celle de la fiche", user)


def regler(ecart, user, commentaire=""):
    ecart.regle_le, ecart.regle_par, ecart.commentaire = timezone.now(), user, commentaire[:255]
    ecart.save(update_fields=['regle_le', 'regle_par', 'commentaire'])
