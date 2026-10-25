# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/services/stats_aides.py
"""
Statistiques des aides financières, MOIS PAR MOIS sur une année, avec cumuls.

Pour chaque aide (AFASE, chèques service, régie d'urgence) :
  - demandes déposées (mois de dépôt)        : nombre, montant demandé
  - accords / refus (mois de la décision)    : nombre, montant accordé
  - envois à la régie (AFASE, mois d'envoi)  : nombre
  - délivrances (mois de délivrance)         : nombre, montant délivré
  - cumuls de l'année : demandé, accordé, délivré
Les brouillons ne comptent pas. Montants en euros.
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.utils import timezone

MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août",
        "Septembre", "Octobre", "Novembre", "Décembre"]
AIDES = [('AFASE', "AFASE"), ('CAP', "Chèques service (CAP)"), ('REGIE', "Régie d'urgence")]


def _jour(valeur):
    """Date (ou date-heure, ramenée à l'heure de Paris) → date."""
    if valeur is None:
        return None
    if hasattr(valeur, 'hour'):
        return timezone.localtime(valeur).date() if timezone.is_aware(valeur) else valeur.date()
    return valeur


def _vide():
    return {'deposees': 0, 'demande': Decimal(0), 'accords': 0, 'accorde': Decimal(0), 'refus': 0,
            'envois_regie': 0, 'delivrees': 0, 'delivre': Decimal(0)}


def dossiers(mds, annee, agent=None):
    """Une ligne par dossier touchant l'année (dépôt, décision ou délivrance dans l'année)."""
    from AidFi.models.m_generique import DemandeAide
    qs = (DemandeAide.objects.filter(beneficiaire__mds=mds).exclude(statut='BROUILLON')
          .select_related('type_aide', 'beneficiaire', 'cree_par'))
    if agent is not None:
        qs = qs.filter(cree_par=agent)
    lignes = []
    for d in qs:
        code = d.type_aide.code if d.type_aide_id else 'AUTRE'
        l = {'demande': d, 'code': code, 'depot': _jour(d.date_creation),
             'montant_demande': d.montant_sollicite or Decimal(0),
             'decision': None, 'accord': None, 'montant_accorde': None,
             'envoi_regie': None, 'delivrance': None, 'montant_delivre': None}
        if code == 'AFASE':
            dec = getattr(getattr(d, 'demandeafase', None), 'decision', None)
            if dec:
                l.update(decision=_jour(dec.date_decision), accord=dec.type_decision == 'ACCORD',
                         montant_accorde=dec.montant_accorde if dec.type_decision == 'ACCORD' else None,
                         envoi_regie=dec.date_envoi_regie, delivrance=dec.date_delivrance,
                         montant_delivre=dec.montant_delivre)
                if dec.type_decision == 'AJO':
                    l['accord'] = None
        elif code == 'CAP':
            cap = getattr(d, 'demandecap', None)
            if cap and cap.date_decision:
                accord = cap.statut != 'REFUSEE'
                l.update(decision=_jour(cap.date_decision), accord=accord,
                         montant_accorde=Decimal(cap.montant_accorde or 0) if accord else None)
            if cap and cap.date_remise:
                l.update(delivrance=_jour(cap.date_remise), montant_delivre=Decimal(cap.montant_accorde or 0))
        elif code == 'REGIE':
            regie = getattr(d, 'regie_urgence', None)
            if regie:
                l.update(decision=l['depot'], accord=True, montant_accorde=regie.montant_urgence)
                if regie.date_versement:
                    l.update(delivrance=_jour(regie.date_versement), montant_delivre=regie.montant_urgence)
        if l['delivrance'] and l['depot']:
            l['delai_jours'] = (l['delivrance'] - l['depot']).days
        if any(x and x.year == annee for x in (l['depot'], l['decision'], l['envoi_regie'], l['delivrance'])):
            lignes.append(l)
    return sorted(lignes, key=lambda l: l['depot'] or date.min)


def calculer(mds, annee, agent=None):
    lignes = dossiers(mds, annee, agent)
    par_aide = {code: [_vide() for _ in range(12)] for code, _ in AIDES}
    for l in lignes:
        mois = par_aide.setdefault(l['code'], [_vide() for _ in range(12)])
        if l['depot'] and l['depot'].year == annee:
            m = mois[l['depot'].month - 1]
            m['deposees'] += 1
            m['demande'] += l['montant_demande']
        if l['decision'] and l['decision'].year == annee:
            m = mois[l['decision'].month - 1]
            if l['accord']:
                m['accords'] += 1
                m['accorde'] += l['montant_accorde'] or 0
            elif l['accord'] is False:
                m['refus'] += 1
        if l['envoi_regie'] and l['envoi_regie'].year == annee:
            mois[l['envoi_regie'].month - 1]['envois_regie'] += 1
        if l['delivrance'] and l['delivrance'].year == annee:
            m = mois[l['delivrance'].month - 1]
            m['delivrees'] += 1
            m['delivre'] += l['montant_delivre'] or 0

    libelles = dict(AIDES)
    aides = []
    for code, mois in par_aide.items():
        cumul = _vide()
        lignes_mois = []
        for i, m in enumerate(mois):
            for k in cumul:
                cumul[k] += m[k]
            lignes_mois.append({'mois': MOIS[i], **m, 'cumul_demande': cumul['demande'],
                                'cumul_accorde': cumul['accorde'], 'cumul_delivre': cumul['delivre']})
        aides.append({'code': code, 'libelle': libelles.get(code, code), 'mois': lignes_mois,
                      'total': dict(cumul), 'a_des_donnees': any(v for v in cumul.values())})
    return {'aides': aides, 'dossiers': lignes, 'annee': annee}


def euros(v):
    return f"{v:.2f}".replace('.', ',') if v is not None else ""


def lignes_csv(resultat):
    yield ["Aide", "Mois", "Demandes déposées", "Montant demandé", "Accords", "Montant accordé", "Refus",
           "Envois à la régie", "Délivrances", "Montant délivré", "Cumul demandé", "Cumul accordé", "Cumul délivré"]
    for a in resultat['aides']:
        if not a['a_des_donnees']:
            continue
        for m in a['mois']:
            yield [a['libelle'], m['mois'], m['deposees'], euros(m['demande']), m['accords'], euros(m['accorde']),
                   m['refus'], m['envois_regie'], m['delivrees'], euros(m['delivre']),
                   euros(m['cumul_demande']), euros(m['cumul_accorde']), euros(m['cumul_delivre'])]
    yield []
    yield ["Dossier", "Usager", "Aide", "Déposé le", "Montant demandé", "Décision le", "Décision",
           "Montant accordé", "Envoyé à la régie le", "Délivré le", "Montant délivré", "Délai (jours)", "Agent"]
    fr = lambda d: d.strftime('%d/%m/%Y') if d else ""
    for l in resultat['dossiers']:
        d = l['demande']
        yield [d.pk, d.beneficiaire.code_interne, l['code'], fr(l['depot']), euros(l['montant_demande']),
               fr(l['decision']), {True: "Accord", False: "Refus", None: ""}[l['accord']],
               euros(l['montant_accorde']), fr(l['envoi_regie']), fr(l['delivrance']), euros(l['montant_delivre']),
               l.get('delai_jours', ""), (d.cree_par.get_full_name() or d.cree_par.username) if d.cree_par else ""]
