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
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from core.phonetique import cle, norme

from core.journal import journaliser

from .models import Beneficiaire

MAX_RESULTATS = 20
AUCUN_RESULTAT = "Aucun usager ne correspond : il n'est peut-être pas encore connu de CID."
# Une recherche concluante (résultats ou réponse « aucun ») ouvre la création pendant ce délai.
CLE_SESSION_RECHERCHE = 'annuaire_recherche_ts'
DUREE_RECHERCHE = timedelta(minutes=60)


def recherche_recente(request):
    """True si l'agent a fait une recherche concluante dans l'annuaire il y a moins de DUREE_RECHERCHE."""
    ts = request.session.get(CLE_SESSION_RECHERCHE)
    if not ts:
        return False
    try:
        moment = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return False
    return timezone.now() - moment <= DUREE_RECHERCHE


def effacer_recherche(request):
    request.session.pop(CLE_SESSION_RECHERCHE, None)


def _distance(a, b):
    """Distance de Levenshtein : nombre de lettres à ajouter, retirer ou changer pour passer de a à b."""
    if a == b:
        return 0
    precedente = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        courante = [i]
        for j, cb in enumerate(b, 1):
            courante.append(min(precedente[j] + 1, courante[j - 1] + 1, precedente[j - 1] + (ca != cb)))
        precedente = courante
    return precedente[-1]


def _nom_proche(demande, trouve):
    """Faute de frappe tolérée (moop → monop) ou même prononciation (Frederik → Frédéric). Une lettre de différence
    jusqu'à 5 caractères, deux au-delà. Un nom absent ne correspond à rien."""
    a, b = norme(demande), norme(trouve)
    if not a or not b:
        return False
    if cle(demande) == cle(trouve):
        return True
    return _distance(a, b) <= (1 if len(a) <= 5 else 2)


def _date_proche(demandee, trouvee):
    """Date identique, jour et mois inversés, ou un seul chiffre différent (ex. 1987 pour 1977 ; 02/03 pour 03/02)."""
    if demandee == trouvee:
        return True
    if demandee.year == trouvee.year and demandee.day == trouvee.month and demandee.month == trouvee.day:
        return True
    a, b = demandee.strftime("%Y%m%d"), trouvee.strftime("%Y%m%d")
    return sum(x != y for x, y in zip(a, b)) == 1


def rechercher(code="", caf="", telephone="", nom="", prenom="", date_naissance=None, adresse=""):
    """Renvoie (résultats, message). Critères insuffisants → aucun résultat et une explication.

    Seuls, un identifiant exact suffit : code usager CID, n° CAF ou téléphone. Sinon il faut deux éléments parmi nom,
    prénom, date de naissance et adresse (même incomplète : « rue montmirail », « port de bouc »). Les réponses exactes
    viennent d'abord ; s'il en reste de la place, les réponses « proches » (faute de frappe, nom à la même
    prononciation, date à un chiffre près ou jour et mois inversés) suivent, marquées `proche`. La ville est comparée
    sans accents, tirets ni espaces. L'agent vérifie toujours la date de naissance."""
    from core.phonetique import chiffres
    code, caf, nom, prenom = (code or "").strip().upper(), (caf or "").strip(), (nom or "").strip(), (prenom or "").strip()
    mots_adresse = [m for m in (norme(x) for x in (adresse or "").replace(",", " ").split()) if len(m) >= 2][:6]
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
        for m in mots_adresse:
            qs = qs.filter(Q(adresse_cle__contains=m) | Q(ville_cle__contains=m) | Q(code_postal=m))
    else:
        return [], ("Indiquez le code usager CID, le n° CAF ou le téléphone, ou deux éléments parmi : nom, prénom, "
                    "date de naissance, adresse.")
    exacts = qs
    if date_naissance:
        exacts = exacts.filter(date_naissance=date_naissance)
    if noms[0]:
        exacts = exacts.filter(Q(nom__icontains=nom) | Q(nom_naissance__icontains=nom))
    if noms[1]:
        exacts = exacts.filter(prenom__icontains=prenom)
    resultats = list(exacts.order_by('nom', 'prenom')[:MAX_RESULTATS + 1])
    if (any(noms) or date_naissance) and len(resultats) <= MAX_RESULTATS:
        deja = {b.pk for b in resultats}
        retenus = []
        for pk, n, nn, p, d in qs.exclude(pk__in=deja).values_list(
                'pk', 'nom', 'nom_naissance', 'prenom', 'date_naissance').iterator():
            if noms[0] and not (_nom_proche(nom, n) or _nom_proche(nom, nn or "")):
                continue
            if noms[1] and not _nom_proche(prenom, p):
                continue
            if date_naissance and not (d and _date_proche(date_naissance, d)):
                continue
            retenus.append(pk)
        if retenus:
            for b in Beneficiaire.objects.select_related('mds').filter(pk__in=retenus).order_by('nom', 'prenom')[
                    :MAX_RESULTATS + 1 - len(resultats)]:
                b.proche = True
                resultats.append(b)
    if len(resultats) > MAX_RESULTATS:
        return resultats[:MAX_RESULTATS], f"Plus de {MAX_RESULTATS} réponses : précisez la recherche."
    return resultats, "" if resultats else AUCUN_RESULTAT


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
        if resultats or message == AUCUN_RESULTAT:
            request.session[CLE_SESSION_RECHERCHE] = timezone.now().isoformat()
        journaliser('READ', "Annuaire des usagers : recherche", request=request, details={
            'criteres': {k: (str(v) if k not in ('caf', 'telephone') else 'oui') for k, v in c.items() if v},
            'resultats': [b.code_interne for b in resultats]})
    lignes = [{'b': b, 'acces': b.niveau_acces(request.user)} for b in resultats]
    from .views import user_peut_creer  # import local : évite un cycle entre les deux modules
    return render(request, 'beneficiaire/annuaire.html', {
        'c': c, 'lignes': lignes, 'message': message, 'cherche': cherche,
        'date_naissance': request.GET.get('date_naissance', ''),
        'aucun_resultat': message == AUCUN_RESULTAT,
        'peut_creer': user_peut_creer(request.user),
        'creation_url': _url_creation(c),
    })


def _url_creation(c):
    """Lien vers la création, prérempli avec ce qui a été recherché (le formulaire reste à valider)."""
    params = {'nom': c['nom'], 'prenom': c['prenom'], 'telephone': c['telephone'], 'adresse': c['adresse']}
    if c['date_naissance']:
        params['date_naissance'] = c['date_naissance'].isoformat()
    params = {k: v for k, v in params.items() if v}
    base = reverse('beneficiaire:ajouter_beneficiaire')
    from urllib.parse import urlencode
    return f"{base}?{urlencode(params)}" if params else base
