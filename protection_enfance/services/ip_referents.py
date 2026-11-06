# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/services/ip_referents.py
"""
Règle (Fred, 6/11/2026) : il n'est PAS RECOMMANDÉ qu'un professionnel qui suit la famille évalue l'IP de cette
famille, quelle que soit la raison de ce suivi (référent MDS, RSA, AFASE ou autre). CID ne le propose pas et prévient
le cadre ; c'est le cadre qui décide et peut passer outre (sous-effectif, PMI qui connaît déjà la famille…) en le
confirmant ; la décision est tracée dans le journal de l'IP. L'accès à l'IP et aux documents ne change pas.

« Suivre la famille » = pour l'une des personnes de l'IP (dossier famille, enfants, adultes rattachés dans CID) :
- être son référent MDS ;
- être référent d'un de ses contrats RSA ;
- avoir instruit une de ses demandes d'aide financière, mené un de ses entretiens ou l'avoir reçue en rendez-vous
  (hors rendez-vous IP / enfance) dans les 24 derniers mois.
"""
from datetime import timedelta

from django.utils import timezone

PERIODE = timedelta(days=730)


def personnes(ip):
    ids = {ip.famille_id} if ip.famille_id else set()
    ids |= {e.beneficiaire_id for e in ip.enfants.all() if e.beneficiaire_id}
    ids |= {a.beneficiaire_id for a in ip.adultes.all() if a.beneficiaire_id}
    return ids


def suivis(ip):
    """{user_id: [raisons]} des professionnels qui suivent la famille."""
    from AidFi.models.m_generique import DemandeAide
    from beneficiaire.models import Beneficiaire, EntretienSocial
    from insertion.models import ContratInsertion
    from planning.models import STATUTS_REALISES, CreneauRdv
    ids = personnes(ip)
    if not ids:
        return {}
    depuis = timezone.now() - PERIODE
    raisons = {}

    def ajouter(uid, raison):
        if uid and raison not in raisons.setdefault(uid, []):
            raisons[uid].append(raison)
    for uid in Beneficiaire.tous.filter(pk__in=ids).values_list('referent_mds_id', flat=True):
        ajouter(uid, "référent(e) MDS de la famille")
    for uid in ContratInsertion.objects.filter(beneficiaire_id__in=ids).values_list('referent_id', flat=True):
        ajouter(uid, "référent(e) RSA")
    for uid in DemandeAide.objects.filter(beneficiaire_id__in=ids, date_creation__gte=depuis).values_list('cree_par_id', flat=True):
        ajouter(uid, "a instruit une aide financière")
    for uid in EntretienSocial.objects.filter(beneficiaire_id__in=ids, date__gte=depuis.date()).values_list('auteur_id', flat=True):
        ajouter(uid, "mène les entretiens d'accompagnement")
    for uid in (CreneauRdv.objects.filter(beneficiaire_id__in=ids, statut__in=STATUTS_REALISES, date__gte=depuis.date())
                .exclude(domaine__in=('IP', 'ENFANCE')).values_list('agent_id', flat=True)):
        ajouter(uid, "a reçu la famille en rendez-vous")
    return raisons


def conflits(ip, utilisateurs, raisons=None):
    """Parmi ces professionnels, ceux qui suivent la famille : [(user, raisons)]."""
    raisons = suivis(ip) if raisons is None else raisons
    return [(u, raisons[u.pk]) for u in utilisateurs if u and u.pk in raisons]
