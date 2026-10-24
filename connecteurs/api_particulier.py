# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/api_particulier.py
"""
Client de l'API Particulier (v3) — situation CAF/MSA et France Travail d'un usager.

Par défaut : BAC À SABLE (https://staging.particulier.api.gouv.fr). Il ne renvoie
que des données fictives, pour les identités de test publiées dans le dépôt
datagouv/apistration (dossier mocks/payloads). Aucune donnée réelle ne circule.

Variables d'environnement (facultatives) :
  API_PARTICULIER_URL        adresse de l'API (défaut : bac à sable)
  API_PARTICULIER_TOKEN      jeton ; obligatoire hors bac à sable (habilitation DataPass)
  API_PARTICULIER_RECIPIENT  SIRET de l'organisme demandeur (en production : celui du CD13)
"""
import logging
import os

import requests
from django.utils import timezone

from .models import SituationExterne, JournalAppelAPI

logger = logging.getLogger(__name__)

URL_BAC_A_SABLE = "https://staging.particulier.api.gouv.fr"
# Jeton PUBLIC du bac à sable (dépôt datagouv/apistration, mocks/tokens/default).
# Il n'ouvre que des données fictives et ne vaut rien en production.
JETON_BAC_A_SABLE = "eyJhbGciOiJIUzI1NiJ9.eyJ1aWQiOiI4YjJjODVmZi00MDIwLTRkNzEtOTA5ZC0zYmU2MzkzM2UzZDciLCJqdGkiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAiLCJzY29wZXMiOlsiYXNzb2NpYXRpb25zIiwib3Blbl9kYXRhIiwicHJvYnRwIiwiY290aXNhdGlvbnNfcHJvYnRwIiwiYXR0ZXN0YXRpb25zX2Zpc2NhbGVzIiwiYXR0ZXN0YXRpb25fZmlzY2FsZV9kZ2ZpcCIsImF0dGVzdGF0aW9uc19zb2NpYWxlcyIsImF0dGVzdGF0aW9uX3NvY2lhbGVfdXJzc2FmIiwiYmlsYW5zX2VudHJlcHJpc2VfYmRmIiwiYmlsYW5zX2JkZiIsImZudHBfY2FydGVfcHJvIiwiY2VydGlmaWNhdF9jbmV0cCIsImNlcnRpZmljYXRpb25fY25ldHAiLCJjZXJ0aWZpY2F0X29wcWliaSIsInF1YWxpYmF0IiwiY2VydGlmaWNhdF9yZ2VfYWRlbWUiLCJkb2N1bWVudHNfYXNzb2NpYXRpb24iLCJlbnRyZXByaXNlcyIsInVuaXRlc19sZWdhbGVzX2V0YWJsaXNzZW1lbnRzX2luc2VlIiwiZXRhYmxpc3NlbWVudHMiLCJleGVyY2ljZXMiLCJjaGlmZnJlX2FmZmFpcmVzX2RnZmlwIiwiZXh0cmFpdHNfcmNzIiwibGlhc3NlX2Zpc2NhbGUiLCJsaWFzc2VzX2Zpc2NhbGVzX2RnZmlwIiwiY2VydGlmaWNhdGlvbnNfcXVhbGlvcGlfZnJhbmNlX2NvbXBldGVuY2VzIiwiYXR0ZXN0YXRpb25fY290aXNhdGlvbnNfY29uZ2VzX3BheWVzX2Nob21hZ2VfaW50ZW1wZXJpZXNfY2lidHBfY25ldHAiLCJlb3JpX2RvdWFuZXMiLCJkYXRhX3N1YnZlbnRpb25fc3VidmVudGlvbnMiLCJsaWVuc19jYXBpdGFsaXN0aXF1ZXNfZGdmaXAiLCJjb252ZW50aW9uc19jb2xsZWN0aXZlcyIsIm1hbmRhdGFpcmVzX3NvY2lhdXhfaW5mb2dyZWZmZSIsImFjdGVzX2lucGkiLCJhc3NvY2lhdGlvbnNfZG9ubmVlc19wcm90ZWdlZXMiLCJhc3NvY2lhdGlvbnNfZGplcHZhIiwiZm9uZGF0aW9uc19taV9zaWFmIiwiYXNzb2NpYXRpb25zX21pX3NpYWYiLCJtc2FfY290aXNhdGlvbnMiLCJjb3Rpc2F0aW9uc19tc2EiLCJjZXJ0aWZpY2F0aW9uX29wcWliaSIsImVudHJlcHJpc2VzX2FydGlzYW5hbGVzIiwiZWZmZWN0aWZzX3Vyc3NhZiIsImJlbmVmaWNpYWlyZXNfZWZmZWN0aWZzX2lucGkiLCJjbmFmX3F1b3RpZW50X2ZhbWlsaWFsIiwiY25hZl9hbGxvY2F0YWlyZXMiLCJjbmFmX2VuZmFudHMiLCJjbmFmX2FkcmVzc2UiLCJjb21wbGVtZW50YWlyZV9zYW50ZV9zb2xpZGFpcmUiLCJhbGxvY2F0aW9uX2FkdWx0ZV9oYW5kaWNhcGUiLCJyZXZlbnVfc29saWRhcml0ZV9hY3RpdmUiLCJyZXZlbnVfc29saWRhcml0ZV9hY3RpdmVfbWFqb3JhdGlvbiIsImFsbG9jYXRpb25fc291dGllbl9mYW1pbGlhbCIsInByaW1lX2FjdGl2aXRlIiwicHJpbWVfYWN0aXZpdGVfbWFqb3JhdGlvbiIsImNub3VzX3N0YXR1dF9ib3Vyc2llciIsImNub3VzX2VjaGVsb25fYm91cnNlIiwiY25vdXNfZW1haWwiLCJjbm91c19wZXJpb2RlX3ZlcnNlbWVudCIsImNub3VzX3N0YXR1dF9ib3Vyc2UiLCJjbm91c192aWxsZV9ldHVkZXMiLCJjbm91c19pZGVudGl0ZSIsIm1lc3JpX2lkZW50aWZpYW50IiwibWVzcmlfaWRlbnRpdGUiLCJtZXNyaV9pbnNjcmlwdGlvbl9ldHVkaWFudCIsIm1lc3JpX2luc2NyaXB0aW9uX2F1dHJlIiwibWVzcmlfYWRtaXNzaW9uIiwibWVzcmlfZXRhYmxpc3NlbWVudHMiLCJwb2xlX2VtcGxvaV9pZGVudGl0ZSIsInBvbGVfZW1wbG9pX2FkcmVzc2UiLCJwb2xlX2VtcGxvaV9jb250YWN0IiwicG9sZV9lbXBsb2lfaW5zY3JpcHRpb24iLCJwb2xlX2VtcGxvaV9wYWllbWVudHMiLCJtZW5fc3RhdHV0X3Njb2xhcml0ZSIsIm1lbl9zdGF0dXRfYm91cnNpZXIiLCJtZW5fZWNoZWxvbl9ib3Vyc2UiLCJhbnRzX2V4dHJhaXRfaW1tYXRyaWN1bGF0aW9uX3ZlaGljdWxlX2lkZW50aXRlX3BhcnRpY3VsaWVyIiwiYW50c19leHRyYWl0X2ltbWF0cmljdWxhdGlvbl92ZWhpY3VsZV9hZHJlc3NlX3BhcnRpY3VsaWVyIiwiYW50c19leHRyYWl0X2ltbWF0cmljdWxhdGlvbl92ZWhpY3VsZV9zdGF0dXRfcmF0dGFjaGVtZW50IiwiYW50c19leHRyYWl0X2ltbWF0cmljdWxhdGlvbl92ZWhpY3VsZV9kb25uZWVzX2ltbWF0cmljdWxhdGlvbl92ZWhpY3VsZSIsImFudHNfZXh0cmFpdF9pbW1hdHJpY3VsYXRpb25fdmVoaWN1bGVfY2FyYWN0ZXJpc3RpcXVlc190ZWNobmlxdWVzX3ZlaGljdWxlIiwicG9sZV9lbXBsb2lfaWRlbnRpZmlhbnQiLCJtZW5fc3RhdHV0X2lkZW50aXRlIiwibWVuX3N0YXR1dF9ldGFibGlzc2VtZW50IiwibWVuX3N0YXR1dF9tb2R1bGVfZWxlbWVudGFpcmVfZm9ybWF0aW9uIiwibWVuX3JlZ2ltZV9wZW5zaW9ubmF0IiwibWVzcmlfYWRtaXNzaW9ucyIsIm1lc3JpX2FkbWlzc2lvbl9pbnNjcml0IiwibWVzcmlfYWRtaXNzaW9uX3JlZ2ltZV9mb3JtYXRpb24iLCJtZXNyaV9hZG1pc3Npb25fY29tbXVuZV9ldHVkZXMiLCJtZXNyaV9hZG1pc3Npb25fZXRhYmxpc3NlbWVudF9ldHVkZXMiLCJjbmF2X2FsbG9jYXRpb25fZW5mYW50X2hhbmRpY2FwZSIsImNuYXZfYWxsb2NhdGlvbl9yZW50cmVlX3Njb2xhaXJlIiwiY25vdXNfaW5lIiwiZHNual9zdGF0dXRfc2VydmljZV9uYXRpb25hbCIsImNuYXZfcGFydGljaXBhdGlvbl9mYW1pbGlhbGVfZWFqZV9hbGxvY2F0YWlyZXMiLCJjbmF2X3BhcnRpY2lwYXRpb25fZmFtaWxpYWxlX2VhamVfZW5mYW50cyIsImNuYXZfcGFydGljaXBhdGlvbl9mYW1pbGlhbGVfZWFqZV9hZHJlc3NlIiwiY25hdl9wYXJ0aWNpcGF0aW9uX2ZhbWlsaWFsZV9lYWplX3BhcmFtZXRyZXNfY2FsY3VsIiwic2RoX3N0YXR1dF9zcG9ydGlmX2lkZW50aXRlIiwic2RoX3N0YXR1dF9zcG9ydGlmX2VzdF9zcG9ydGlmX2RlX2hhdXRfbml2ZWF1Iiwic2RoX3N0YXR1dF9zcG9ydGlmX2FfZXRlX3Nwb3J0aWZfZGVfaGF1dF9uaXZlYXUiLCJzZGhfc3RhdHV0X3Nwb3J0aWZfaW5mb3JtYXRpb25zX3N0YXR1dCIsInNkaF9zdGF0dXRfc3BvcnRpZl9pbmZvcm1hdGlvbnNfc3RhdHV0c19wcmVjZWRlbnRzIiwiZ2lwX21kc19zZXJ2aWNlX2NpdmlxdWVfc3RhdHV0X2FjdHVlbCIsImdpcF9tZHNfc2VydmljZV9jaXZpcXVlX3N0YXR1dF9wYXNzZSIsImdpcF9tZHNfc2VydmljZV9jaXZpcXVlX29yZ2FuaXNtZV9hY2N1ZWlsIiwiZ2lwX21kc19zZXJ2aWNlX2NpdmlxdWVfZGF0ZXMiXSwic3ViIjoic3RhZ2luZyIsImlhdCI6MTc4ODM1Njk5MCwidmVyc2lvbiI6IjEuMCIsImV4cCI6MjEwMzk3NjE5MH0.WAoQoMCtdz4TkThsTT38DEItHXK_gATdt_7ixIXINo4"
SIRET_BAC_A_SABLE = "13002526500013"


def configuration():
    url = os.environ.get('API_PARTICULIER_URL', URL_BAC_A_SABLE).strip().rstrip('/')
    bac_a_sable = (url == URL_BAC_A_SABLE)
    jeton = os.environ.get('API_PARTICULIER_TOKEN', '').strip() or (JETON_BAC_A_SABLE if bac_a_sable else '')
    return {
        'url': url,
        'jeton': jeton,
        'recipient': os.environ.get('API_PARTICULIER_RECIPIENT', SIRET_BAC_A_SABLE).strip(),
        'environnement': 'bac_a_sable' if bac_a_sable else 'production',
    }


class FicheIncomplete(Exception):
    """Il manque une information d'état civil pour interroger l'organisme."""


# =============================================================================
# PARAMÈTRES D'IDENTITÉ
# =============================================================================

def parametres_identite(b):
    """Identité au format de l'API (nom de naissance, prénoms, date, lieu, sexe)."""
    manque = []
    if not b.date_naissance:
        manque.append("date de naissance")
    pays = (b.code_pays_naissance or '').strip() or '99100'
    commune = (b.code_insee_naissance or '').strip()
    if pays == '99100' and not commune:
        manque.append("code INSEE de la commune de naissance")
    if b.civilite not in ('M.', 'MME'):
        manque.append("civilité")
    if manque:
        raise FicheIncomplete("À compléter sur la fiche : " + ", ".join(manque) + ".")

    params = {
        'nomNaissance': (b.nom_naissance or b.nom).strip().upper(),
        'prenoms[]': [p for p in (b.prenom or '').upper().replace(',', ' ').split() if p],
        'anneeDateNaissance': b.date_naissance.year,
        'moisDateNaissance': b.date_naissance.month,
        'jourDateNaissance': b.date_naissance.day,
        'codeCogInseePaysNaissance': pays,
        'sexeEtatCivil': 'M' if b.civilite == 'M.' else 'F',
    }
    if b.nom_naissance and b.nom and b.nom_naissance.strip().upper() != b.nom.strip().upper():
        params['nomUsage'] = b.nom.strip().upper()
    if pays == '99100':
        params['codeCogInseeCommuneNaissance'] = commune
    return params


def _parametres_france_travail(b):
    if not (b.numero_france_travail or '').strip():
        raise FicheIncomplete("À compléter sur la fiche : identifiant France Travail.")
    return {'identifiant': b.numero_france_travail.strip()}


# =============================================================================
# LECTURE DES RÉPONSES (résumé + données minimisées)
# =============================================================================

def _date_fr(iso):
    if not iso:
        return ""
    a, m, j = iso[:10].split('-')
    return f"{j}/{m}/{a}"


def _lire_droit(libelle, cle_option=None, texte_option=""):
    def lire(data):
        if not data.get('est_beneficiaire'):
            return False, f"Pas de droit {libelle} ouvert", {'est_beneficiaire': False}
        depuis = _date_fr(data.get('date_debut_droit'))
        resume = f"Droit {libelle} ouvert" + (f" depuis le {depuis}" if depuis else "")
        utile = {'est_beneficiaire': True, 'date_debut_droit': data.get('date_debut_droit')}
        if cle_option:
            utile[cle_option] = data.get(cle_option)
            if data.get(cle_option):
                resume += f" ({texte_option})"
        return True, resume, utile
    return lire


def _lire_qf(data):
    qf = data.get('quotient_familial') or {}
    if qf.get('valeur') is None:
        return None, "Quotient familial non communiqué", {}
    periode = f"{int(qf['mois']):02d}/{qf['annee']}" if qf.get('mois') and qf.get('annee') else ""
    enfants = len(data.get('enfants') or [])
    resume = f"QF {qf.get('fournisseur', '')} : {qf['valeur']} €" + (f" ({periode})" if periode else "")
    resume += f" – {enfants} enfant{'s' if enfants > 1 else ''} rattaché{'s' if enfants > 1 else ''}"
    utile = {'fournisseur': qf.get('fournisseur'), 'valeur': qf['valeur'],
             'mois': qf.get('mois'), 'annee': qf.get('annee'), 'nb_enfants': enfants}
    return True, resume, utile


def _lire_france_travail(data):
    ins = data.get('inscription') or {}
    debut, fin = ins.get('date_debut'), ins.get('date_fin')
    categorie = (ins.get('categorie') or {})
    utile = {'date_debut': debut, 'date_fin': fin,
             'categorie_code': categorie.get('code'), 'categorie': categorie.get('libelle')}
    if fin and fin <= timezone.localdate().isoformat():
        return False, f"Désinscrit(e) depuis le {_date_fr(fin)}", utile
    resume = "Inscrit(e)" + (f" depuis le {_date_fr(debut)}" if debut else "")
    if categorie.get('code'):
        resume += f" – catégorie {categorie['code']}"
    return True, resume, utile


SERVICES = {
    'RSA': {'chemin': '/v3/dss/revenu_solidarite_active/identite',
            'lire': _lire_droit("RSA", 'avec_majoration', "majoré")},
    'PRIME_ACTIVITE': {'chemin': '/v3/dss/prime_activite/identite',
                       'lire': _lire_droit("prime d'activité", 'avec_majoration', "majorée")},
    'QUOTIENT_FAMILIAL': {'chemin': '/v3/dss/quotient_familial/identite', 'lire': _lire_qf},
    'ASF': {'chemin': '/v3/dss/allocation_soutien_familial/identite', 'lire': _lire_droit("ASF")},
    'AAH': {'chemin': '/v3/dss/allocation_adulte_handicape/identite', 'lire': _lire_droit("AAH")},
    'C2S': {'chemin': '/v3/dss/complementaire_sante_solidaire/identite',
            'lire': _lire_droit("C2S", 'avec_participation', "avec participation financière")},
    'FRANCE_TRAVAIL': {'chemin': '/v3/france_travail/statut/identifiant', 'lire': _lire_france_travail,
                       'parametres': _parametres_france_travail},
}


# =============================================================================
# APPEL ET ENREGISTREMENT
# =============================================================================

def interroger(source, beneficiaire):
    """Appelle l'organisme. Retourne (statut_appel, code_http, est_beneficiaire, resume, donnees)."""
    service = SERVICES[source]
    conf = configuration()
    try:
        params = service.get('parametres', parametres_identite)(beneficiaire)
    except FicheIncomplete as e:
        return 'INCOMPLET', None, None, str(e), {}
    if not conf['jeton']:
        return 'ERREUR', None, None, "Jeton API Particulier absent (API_PARTICULIER_TOKEN).", {}

    params['recipient'] = conf['recipient']
    try:
        r = requests.get(conf['url'] + service['chemin'], params=params, timeout=20,
                         headers={'Authorization': f"Bearer {conf['jeton']}", 'Accept': 'application/json'})
    except requests.RequestException as e:
        logger.warning("API Particulier %s injoignable : %s", source, e)
        return 'ERREUR', None, None, "Service injoignable, réessayez plus tard.", {}

    if r.status_code == 404:
        return 'NON_TROUVE', 404, None, "Personne inconnue de l'organisme (vérifier l'état civil).", {}
    if r.status_code == 422:
        return 'NON_TROUVE', 422, None, "Identité insuffisante ou ambiguë pour l'organisme.", {}
    if r.status_code != 200:
        logger.warning("API Particulier %s : HTTP %s", source, r.status_code)
        return 'ERREUR', r.status_code, None, f"Service indisponible (code {r.status_code}).", {}

    est, resume, utile = service['lire'](r.json().get('data') or {})
    return 'OK', 200, est, resume, utile


def actualiser(beneficiaire, user, sources=None):
    """Interroge les organismes et enregistre la situation avec la date du jour."""
    conf = configuration()
    resultats = []
    for source in (sources or SERVICES.keys()):
        statut, code, est, resume, utile = interroger(source, beneficiaire)
        JournalAppelAPI.objects.create(beneficiaire=beneficiaire, source=source, utilisateur=user,
                                       code_http=code, statut_appel=statut,
                                       environnement=conf['environnement'])
        existante = SituationExterne.objects.filter(beneficiaire=beneficiaire, source=source).first()
        if statut == 'ERREUR' and existante and existante.statut_appel == 'OK':
            # Panne passagère : on garde la dernière information valable (et sa date)
            resultats.append(existante)
            continue
        situation, _ = SituationExterne.objects.update_or_create(
            beneficiaire=beneficiaire, source=source,
            defaults={'statut_appel': statut, 'resume': resume[:255], 'est_beneficiaire': est,
                      'donnees': utile, 'date_maj': timezone.now(), 'maj_par': user,
                      'environnement': conf['environnement']},
        )
        resultats.append(situation)
    return resultats


def tableau_situations(beneficiaire):
    """Pour la fiche usager : toutes les sources, avec la dernière information connue (ou rien)."""
    from .models import SOURCES
    connues = {s.source: s for s in beneficiaire.situations_externes.select_related('maj_par')}
    return {
        'lignes': [{'code': code, 'libelle': libelle, 'situation': connues.get(code)} for code, libelle in SOURCES],
        'environnement': configuration()['environnement'],
    }
