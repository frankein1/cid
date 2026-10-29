# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/services/afase_delais.py
"""
Délais réglementaires d'une AFASE :
  - ajournement : sans réponse du travailleur social dans les 15 jours, le cadre refuse (absence de justificatifs) ;
  - silence de l'administration : la demande est réputée refusée 2 mois après la date de signature du demandeur.
CID ne change jamais le statut tout seul : il affiche l'échéance et prévient, une seule fois par rappel,
la personne qui doit agir.
"""
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.utils import timezone

DELAI_AJOURNEMENT = 15          # jours
RAPPEL_AJOURNEMENT_TS = 10      # jours après l'ajournement
ALERTE_DEUX_MOIS = 15           # jours avant l'échéance des 2 mois
STATUTS_EN_ATTENTE = ("EN_INSTRUCTION", "DEPOSEE", "AJO")


def echeance_deux_mois(demande):
    if not demande.date_signature_demandeur:
        return None
    return demande.date_signature_demandeur + relativedelta(months=2)


def echeance_ajournement(demande):
    if demande.statut != "AJO" or not demande.date_ajournement:
        return None
    return timezone.localdate(demande.date_ajournement) + timedelta(days=DELAI_AJOURNEMENT)


def etat(demande, aujourd_hui=None):
    """Échéances d'une demande, pour l'affichage. None si la demande n'est plus en attente."""
    if demande.statut not in STATUTS_EN_ATTENTE:
        return None
    jour = aujourd_hui or timezone.localdate()
    e2 = echeance_deux_mois(demande)
    ea = echeance_ajournement(demande)
    res = {
        "echeance_2_mois": e2,
        "jours_2_mois": (e2 - jour).days if e2 else None,
        "reputee_refusee": bool(e2 and jour >= e2),
        "echeance_ajournement": ea,
        "jours_ajournement": (ea - jour).days if ea else None,
        "ajournement_echu": bool(ea and jour >= ea),
    }
    res["alerte"] = bool(res["reputee_refusee"] or res["ajournement_echu"]
                         or (e2 and res["jours_2_mois"] <= ALERTE_DEUX_MOIS))
    return res


def decideurs(demande):
    """Ceux qui doivent décider : les inspecteurs (mesure ASE) ou le responsable de la MDS."""
    from beneficiaire.transfert import responsable_mds
    from core.models import User
    if demande.decision_inspecteur:
        return list(User.objects.filter(is_active=True, profils__code='PIEF', profils__actif=True).distinct())
    r = responsable_mds(demande.mds)
    return [r] if r else []


def _prevenir(demande, cle, destinataires, objet, contenu, expediteur):
    from AidFi.signals import _envoyer
    if cle in (demande.rappels_envoyes or []):
        return 0
    n = 0
    for dest in destinataires:
        if dest and expediteur:
            _envoyer(expediteur, dest, demande, objet=objet, contenu=contenu + "\n\nMessage automatique de CID.",
                     motif='validation_cadre', priorite='importante')
            n += 1
    demande.rappels_envoyes = (demande.rappels_envoyes or []) + [cle]
    demande.save(update_fields=["rappels_envoyes"])
    return n


def envoyer_rappels(demande, aujourd_hui=None):
    """Envoie les rappels dus pour cette demande (chacun une seule fois). Retourne le nombre de messages."""
    e = etat(demande, aujourd_hui)
    if not e:
        return 0
    b = demande.beneficiaire
    qui = f"{b.prenom} {b.nom.upper()} (dossier AFASE {demande.pk})"
    ts = demande.cree_par
    cadres = decideurs(demande)
    expediteur_cadre = cadres[0] if cadres else ts
    n = 0
    if e["echeance_ajournement"]:
        jours = e["jours_ajournement"]
        suffixe = demande.date_ajournement.strftime("%Y%m%d")
        if jours <= DELAI_AJOURNEMENT - RAPPEL_AJOURNEMENT_TS and not e["ajournement_echu"]:
            n += _prevenir(demande, f"ajo_ts_{suffixe}", [ts],
                           f"AFASE ajournée : plus que {jours} jour(s) pour compléter – {qui}",
                           f"La demande d'AFASE de {qui} a été ajournée. Sans réponse avant le "
                           f"{e['echeance_ajournement']:%d/%m/%Y}, elle sera refusée pour absence de justificatifs.",
                           expediteur_cadre)
        if e["ajournement_echu"]:
            n += _prevenir(demande, f"ajo_cadre_{suffixe}", cadres,
                           f"AFASE ajournée sans réponse depuis 15 jours – {qui}",
                           f"Le travailleur social n'a pas complété la demande d'AFASE de {qui} dans les 15 jours "
                           f"suivant l'ajournement. Elle est à refuser pour absence de justificatifs (code refus 1).",
                           ts or expediteur_cadre)
    if e["echeance_2_mois"]:
        if e["reputee_refusee"]:
            n += _prevenir(demande, "deux_mois_echu", cadres + ([ts] if ts and ts not in cadres else []),
                           f"AFASE réputée refusée (2 mois sans décision) – {qui}",
                           f"La demande d'AFASE de {qui}, signée le {demande.date_signature_demandeur:%d/%m/%Y}, est "
                           f"sans décision depuis 2 mois : elle est réputée refusée depuis le "
                           f"{e['echeance_2_mois']:%d/%m/%Y}. Une décision expresse reste à prendre et à notifier.",
                           expediteur_cadre)
        elif e["jours_2_mois"] <= ALERTE_DEUX_MOIS and demande.statut == "DEPOSEE":
            n += _prevenir(demande, "deux_mois_j15", cadres,
                           f"AFASE à décider avant le {e['echeance_2_mois']:%d/%m/%Y} – {qui}",
                           f"Sans décision avant le {e['echeance_2_mois']:%d/%m/%Y} (2 mois après la signature du "
                           f"demandeur), la demande d'AFASE de {qui} sera réputée refusée.",
                           ts or expediteur_cadre)
    return n


def envoyer_tous_les_rappels(aujourd_hui=None, qs=None):
    from AidFi.models import DemandeAFASE
    qs = qs if qs is not None else DemandeAFASE.objects.filter(statut__in=STATUTS_EN_ATTENTE)
    return sum(envoyer_rappels(d, aujourd_hui) for d in qs.select_related('beneficiaire__mds', 'cree_par'))
