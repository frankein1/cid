# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/services/aide_decision.py
"""
Aide à la décision d'une AFASE : reste à vivre situé par rapport aux seuils, montant indicatif du motif
selon le nombre d'enfants concernés, aides de droit commun à mobiliser, historique des 12 derniers mois
et contrôle UAGAF renforcé. Les valeurs viennent du référentiel saisi dans l'administration.
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from AidFi.models.m_referentiel import MontantIndicatifAFASE, ParametresAides, ReferentielMotifAFASE


def referentiel():
    """{code: {...}} pour l'affichage (et le JavaScript des pages de saisie et de décision)."""
    sortie = {}
    for m in ReferentielMotifAFASE.objects.filter(actif=True).prefetch_related('montants'):
        sortie[m.code] = {
            'libelle': m.libelle, 'aides': m.liste_aides, 'conditions': m.conditions,
            'montants': [{'critere': x.critere, 'nb_enfants': x.nb_enfants, 'montant': str(x.montant),
                          'par_mois': x.par_mois} for x in m.montants.all()],
        }
    return sortie


def montant_indicatif(code, nb_enfants):
    """Montant indicatif selon le nombre d'enfants (la plus grande valeur saisie vaut « et plus »)."""
    lignes = list(MontantIndicatifAFASE.objects.filter(motif__code=code, motif__actif=True,
                                                       nb_enfants__isnull=False).order_by('nb_enfants'))
    if not lignes or not nb_enfants:
        return None
    retenu = [l for l in lignes if l.nb_enfants <= nb_enfants]
    return (retenu[-1] if retenu else lignes[0])


def _famille(beneficiaire):
    return {beneficiaire.pk} | {m['personne'].pk for m in beneficiaire.reseau_familial()}


def historique_12_mois(demande):
    """AFASE accordées à la famille sur les 12 derniers mois (hors la demande en cours)."""
    from AidFi.models.m_afase import DecisionAFASE
    depuis = timezone.now() - timedelta(days=365)
    decisions = (DecisionAFASE.objects.filter(type_decision='ACCORD', date_decision__gte=depuis,
                                              demande__beneficiaire_id__in=_famille(demande.beneficiaire))
                 .exclude(demande_id=demande.pk).select_related('demande').order_by('-date_decision'))
    total = sum(((d.montant_accorde or Decimal(0)) * (d.duree_accordee or 1) for d in decisions), Decimal(0))
    return {'decisions': list(decisions), 'nombre': len(decisions), 'total': total}


def analyse(demande):
    p = ParametresAides.actuels()
    budget = getattr(demande, 'budget', None)
    rav = budget.reste_a_vivre if budget else None
    zone = None
    if rav is not None and p.rav_seuil_accord is not None and p.rav_seuil_parentalite is not None:
        zone = ('accord' if rav < p.rav_seuil_accord
                else 'parentalite' if rav > p.rav_seuil_parentalite else 'evaluer')
    nb_enfants = demande.enfants.filter(concerne=True).count() if demande.pk else 0
    hist = historique_12_mois(demande)
    total_demande = (demande.montant_sollicite or Decimal(0)) * (demande.duree_demande or 1)
    alertes = []
    if p.seuil_montant_controle is not None and total_demande > p.seuil_montant_controle:
        alertes.append(f"Demande de plus de {p.seuil_montant_controle:.0f} € : contrôle de conformité renforcé de l'UAGAF, "
                       "qui peut interpeller la direction de la MDS ou de la DITAS pour révision ou confirmation du montant.")
    if p.seuil_nb_aides_12_mois is not None and hist['nombre'] >= p.seuil_nb_aides_12_mois:
        alertes.append(f"{hist['nombre']} AFASE déjà accordées sur les 12 derniers mois : contrôle de conformité renforcé "
                       "de l'UAGAF (demandes récurrentes).")
    return {
        'parametres': p, 'rav': rav, 'zone_rav': zone, 'nb_enfants': nb_enfants, 'historique': hist,
        'total_demande': total_demande, 'alertes': alertes,
        'motif': ReferentielMotifAFASE.objects.filter(code=demande.motif_envisage).first()
        if demande.motif_envisage else None,
        'montant_indicatif': montant_indicatif(demande.motif_envisage, nb_enfants) if demande.motif_envisage else None,
    }


# -----------------------------------------------------------------------------
# Import / export du référentiel (fichier JSON préparé à partir de la note de service)
# -----------------------------------------------------------------------------

CHAMPS_PARAMETRES = ('reference_note', 'seuil_montant_controle', 'seuil_nb_aides_12_mois', 'rav_seuil_accord',
                     'rav_seuil_parentalite', 'participation_famille_pct', 'regie_montant_max')


def exporter():
    p = ParametresAides.actuels()
    return {
        'parametres': {c: (getattr(p, c) if isinstance(getattr(p, c), (int, str)) or getattr(p, c) is None
                           else str(getattr(p, c))) for c in CHAMPS_PARAMETRES},
        'motifs': [{'code': m.code, 'libelle': m.libelle, 'aides_prealables': m.aides_prealables,
                    'conditions': m.conditions, 'actif': m.actif,
                    'montants': [{'critere': x.critere, 'nb_enfants': x.nb_enfants, 'montant': str(x.montant),
                                  'par_mois': x.par_mois} for x in m.montants.all()]}
                   for m in ReferentielMotifAFASE.objects.prefetch_related('montants')],
    }


def _decimal(v):
    if v in (None, ''):
        return None
    try:
        return Decimal(str(v).replace(',', '.'))
    except InvalidOperation:
        raise ValueError(f"Valeur numérique invalide : {v}")


@transaction.atomic
def importer(data):
    """Remplace paramètres et motifs par ceux du fichier. Retourne un résumé."""
    if not isinstance(data, dict) or 'motifs' not in data:
        raise ValueError("Fichier non reconnu : il doit contenir « parametres » et « motifs ».")
    p = ParametresAides.objects.first() or ParametresAides()
    for c in CHAMPS_PARAMETRES:
        if c in (data.get('parametres') or {}):
            v = data['parametres'][c]
            if c == 'reference_note':
                p.reference_note = (v or '')[:200]
            elif c in ('seuil_nb_aides_12_mois', 'participation_famille_pct'):
                setattr(p, c, int(v) if v not in (None, '') else None)
            else:
                setattr(p, c, _decimal(v))
    p.save()
    n = 0
    for m in data['motifs']:
        code = str(m.get('code', '')).strip()
        if not code:
            continue
        ref, _ = ReferentielMotifAFASE.objects.get_or_create(code=code, defaults={'libelle': m.get('libelle') or code})
        ref.libelle = (m.get('libelle') or ref.libelle)[:150]
        ref.aides_prealables = m.get('aides_prealables', '') or ''
        ref.conditions = m.get('conditions', '') or ''
        ref.actif = m.get('actif', True)
        ref.save()
        ref.montants.all().delete()
        for x in m.get('montants') or []:
            MontantIndicatifAFASE.objects.create(motif=ref, critere=(x.get('critere') or '')[:100],
                                                 nb_enfants=x.get('nb_enfants'), montant=_decimal(x.get('montant')),
                                                 par_mois=x.get('par_mois', True))
        n += 1
    return f"{n} motif(s) importé(s), paramètres mis à jour."
