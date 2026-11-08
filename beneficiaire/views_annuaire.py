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
La recherche exige un identifiant exact (code usager, n° CAF, téléphone) ou deux éléments parmi nom, prénom, date de
naissance et adresse : on ne peut pas parcourir l'annuaire. Les orthographes proches sont proposées à part. Chaque recherche est inscrite au journal d'activité."""
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from core.journal import journaliser

from .models import Beneficiaire

MAX_RESULTATS = 20


def rechercher(code="", caf="", telephone="", nom="", prenom="", date_naissance=None, adresse=""):
    """Renvoie (résultats, message). Critères insuffisants → aucun résultat et une explication.

    Seuls, un identifiant exact suffit : code usager CID, n° CAF ou téléphone. Sinon il faut deux éléments parmi nom,
    prénom, date de naissance et adresse (même incomplète : « rue montmirail »). Après les réponses exactes viennent
    les « orthographes proches » (même prononciation : Frederik → Frédéric, Frédérique…), marquées `proche`."""
    from core.phonetique import chiffres, cle
    code, caf, nom, prenom = (code or "").strip().upper(), (caf or "").strip(), (nom or "").strip(), (prenom or "").strip()
    mots_adresse = [m for m in (adresse or "").replace(",", " ").split() if len(m) >= 2][:6]
    tel = chiffres(telephone)
    qs = Beneficiaire.objects.select_related('mds').exclude(statut='ARCHIVE')
    noms = len(nom) >= 2, len(prenom) >= 2
    if code:
        qs, noms = qs.filter(code_interne__iexact=code), (False, False)
    elif caf:
        qs, noms = qs.filter(numero_caf=caf), (False, False)
    elif len(tel) == 9:
        qs, noms = qs.filter(Q(telephone_mobile_cle=tel) | Q(telephone_fixe_cle=tel)), (False, False)
    elif sum((*noms, bool(date_naissance), bool(mots_adresse))) >= 2:
        if date_naissance:
            qs = qs.filter(date_naissance=date_naissance)
        for m in mots_adresse:
            qs = qs.filter(Q(adresse__icontains=m) | Q(ville__icontains=m) | Q(code_postal=m))
    else:
        return [], ("Indiquez le code usager CID, le n° CAF ou le téléphone, ou deux éléments parmi : nom, prénom, "
                    "date de naissance, adresse.")
    exacts = qs
    if noms[0]:
        exacts = exacts.filter(Q(nom__icontains=nom) | Q(nom_naissance__icontains=nom))
    if noms[1]:
        exacts = exacts.filter(prenom__icontains=prenom)
    resultats = list(exacts.order_by('nom', 'prenom')[:MAX_RESULTATS + 1])
    if any(noms) and len(resultats) <= MAX_RESULTATS:
        proches = qs.exclude(pk__in=[b.pk for b in resultats])
        if noms[0] and cle(nom):
            proches = proches.filter(Q(nom_phonetique=cle(nom)) | Q(nom_naissance_phonetique=cle(nom))
                                     | Q(nom__icontains=nom) | Q(nom_naissance__icontains=nom))
        if noms[1] and cle(prenom):
            proches = proches.filter(Q(prenom_phonetique=cle(prenom)) | Q(prenom__icontains=prenom))
        for b in proches.order_by('nom', 'prenom')[:MAX_RESULTATS + 1 - len(resultats)]:
            b.proche = True
            resultats.append(b)
    if len(resultats) > MAX_RESULTATS:
        return resultats[:MAX_RESULTATS], f"Plus de {MAX_RESULTATS} réponses : précisez la recherche."
    return resultats, "" if resultats else "Aucun usager ne correspond : il n'est peut-être pas encore connu de CID."


def criteres(get):
    from django.utils.dateparse import parse_date
    return {'code': get.get('code', ''), 'caf': get.get('caf', ''), 'telephone': get.get('telephone', ''),
            'nom': get.get('nom', ''), 'prenom': get.get('prenom', ''),
            'date_naissance': parse_date(get.get('date_naissance') or ''), 'adresse': get.get('adresse', '')}


@login_required
def annuaire_usagers(request):
    c = criteres(request.GET)
    resultats, message, cherche = [], "", any(c.values())
    if cherche:
        resultats, message = rechercher(**c)
        journaliser('READ', "Annuaire des usagers : recherche", request=request, details={
            'criteres': {k: (str(v) if k not in ('caf', 'telephone') else 'oui') for k, v in c.items() if v},
            'resultats': [b.code_interne for b in resultats]})
    lignes = [{'b': b, 'acces': b.niveau_acces(request.user)} for b in resultats]
    return render(request, 'beneficiaire/annuaire.html', {
        'c': c, 'lignes': lignes, 'message': message, 'cherche': cherche,
        'date_naissance': request.GET.get('date_naissance', '')})
