# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/views_annuaire.py
"""Annuaire des usagers : tout agent de CID (Service Logement, pôles, services centraux…) peut vérifier si un usager
existe et à quelle MDS il est rattaché, pour saisir ses dossiers avec le code usager CID ou le n° CAF et éviter les
doubles saisies.

On ne voit que l'identité de base : nom, prénom, nom de naissance, date et lieu de naissance, code usager, MDS.
La recherche exige un identifiant exact (code usager, n° CAF) ou deux éléments parmi nom, prénom et date de naissance :
on ne peut pas parcourir l'annuaire. Chaque recherche est inscrite au journal d'activité."""
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from core.journal import journaliser

from .models import Beneficiaire

MAX_RESULTATS = 20


def rechercher(code="", caf="", nom="", prenom="", date_naissance=None):
    """Renvoie (résultats, message). Critères insuffisants → aucun résultat et une explication."""
    code, caf, nom, prenom = (code or "").strip().upper(), (caf or "").strip(), (nom or "").strip(), (prenom or "").strip()
    qs = Beneficiaire.objects.select_related('mds').exclude(statut='ARCHIVE')
    if code:
        qs = qs.filter(code_interne__iexact=code)
    elif caf:
        qs = qs.filter(numero_caf=caf)
    elif sum((len(nom) >= 2, len(prenom) >= 2, bool(date_naissance))) >= 2:
        if len(nom) >= 2:
            qs = qs.filter(Q(nom__icontains=nom) | Q(nom_naissance__icontains=nom))
        if len(prenom) >= 2:
            qs = qs.filter(prenom__icontains=prenom)
        if date_naissance:
            qs = qs.filter(date_naissance=date_naissance)
    else:
        return [], ("Indiquez le code usager CID ou le n° CAF, ou deux éléments parmi : nom, prénom, date de naissance.")
    resultats = list(qs.order_by('nom', 'prenom')[:MAX_RESULTATS + 1])
    if len(resultats) > MAX_RESULTATS:
        return resultats[:MAX_RESULTATS], f"Plus de {MAX_RESULTATS} réponses : précisez la recherche."
    return resultats, "" if resultats else "Aucun usager ne correspond : il n'est peut-être pas encore connu de CID."


def criteres(get):
    from django.utils.dateparse import parse_date
    return {'code': get.get('code', ''), 'caf': get.get('caf', ''), 'nom': get.get('nom', ''),
            'prenom': get.get('prenom', ''), 'date_naissance': parse_date(get.get('date_naissance') or '')}


@login_required
def annuaire_usagers(request):
    c = criteres(request.GET)
    resultats, message, cherche = [], "", any(c.values())
    if cherche:
        resultats, message = rechercher(**c)
        journaliser('READ', "Annuaire des usagers : recherche", request=request, details={
            'criteres': {k: str(v) for k, v in c.items() if v and k != 'caf'} | ({'caf': 'oui'} if c['caf'] else {}),
            'resultats': [b.code_interne for b in resultats]})
    lignes = [{'b': b, 'acces': b.niveau_acces(request.user)} for b in resultats]
    return render(request, 'beneficiaire/annuaire.html', {
        'c': c, 'lignes': lignes, 'message': message, 'cherche': cherche,
        'date_naissance': request.GET.get('date_naissance', '')})
