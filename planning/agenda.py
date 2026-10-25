# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/agenda.py
"""
Agenda unifié : permanences et rendez-vous de l'agent dans un seul calendrier.

Lecture d'un bloc :
  - couleur du fond  = DOMAINE (Social vert, IP rouge, Enfance violet, Insertion bleu,
                       Institutionnel orange) ; clair = prévu, plein = réalisé ;
  - icône            = NATURE (VAD, hors permanence, partenaire…) ;
  - pâle et barré    = annulé, reporté ou absent ;
  - gris + icône     = vu par un collègue qui n'a pas accès au détail (« Occupé ») ;
  - blanc pointillé  = créneau de permanence libre ;
  - noir             = agent indisponible (congés, formation, maladie).
"""
from django.db.models import Q

from .models import (CreneauRdv, DOMAINES_RDV, NATURES_RDV, STATUTS_ANNULES,
                     STATUTS_REALISES)

ICONES_NATURE = {
    'PERMANENCE': '🏢', 'VAD': '🏠', 'HORS_PERMANENCE': '🚪', 'PARTENAIRE': '🤝',
    'TELEPHONIQUE': '📞', 'REUNION': '👥', 'AUTRE': '•',
}

# (prévu = clair, réalisé = plein) ; texte foncé sur clair, blanc sur plein
COULEURS_DOMAINE = {
    'SOCIAL': ('#86EFAC', '#16A34A'),
    'IP': ('#FCA5A5', '#DC2626'),
    'ENFANCE': ('#C4B5FD', '#7C3AED'),
    'INSERTION': ('#93C5FD', '#2563EB'),
    'INSTITUTIONNEL': ('#FDBA74', '#EA580C'),
}
GRIS_OCCUPE = '#D1D5DB'
NOIR_INDISPONIBLE = '#111827'

# Motifs proposés à l'agent (une seule liste « nature – domaine ») : tout sauf la permanence
# (créée par le cadre) et la réunion (lot 2 : convocation par le cadre ou l'administratif)
NATURES_AGENT = ['VAD', 'HORS_PERMANENCE', 'PARTENAIRE', 'TELEPHONIQUE', 'AUTRE']


def choix_motifs():
    natures = dict(NATURES_RDV)
    return [(f"{n}|{d}", f"{natures[n]} – {libelle}") for n in NATURES_AGENT for d, libelle in DOMAINES_RDV]


def legende():
    """Pour le gabarit : domaines (couleurs), natures (icônes), états."""
    return {
        'domaines': [{'libelle': lib, 'prevu': COULEURS_DOMAINE[code][0], 'realise': COULEURS_DOMAINE[code][1]}
                     for code, lib in DOMAINES_RDV],
        'natures': [{'icone': ICONES_NATURE[code], 'libelle': lib} for code, lib in NATURES_RDV],
        'gris': GRIS_OCCUPE, 'noir': NOIR_INDISPONIBLE,
    }


def _heure(t):
    return t.strftime('%H:%M:%S')


def evenement(c, user):
    """Bloc FullCalendar pour un rendez-vous ou un créneau, selon ce que l'utilisateur a le droit de voir
    (None : rien à afficher pour lui)."""
    base = {
        'id': c.id,
        'start': f"{c.date.isoformat()}T{_heure(c.heure_debut)}",
        'end': f"{c.date.isoformat()}T{_heure(c.heure_fin)}",
    }
    icone = ICONES_NATURE.get(c.nature, '•')
    reunion = c.nature == 'REUNION'
    if reunion:
        participants = list(c.co_intervenants.all())
        nom_agent = f"Réunion – {len(participants)} participant{'s' if len(participants) > 1 else ''}"
    else:
        nom_agent = (c.agent.get_full_name() or c.agent.username) if c.agent else "Non assigné"

    # Créneau de permanence libre : blanc pointillé, réservable
    if c.statut == 'DISPONIBLE':
        return {**base, 'title': f"{icone} Libre – {nom_agent}",
                'backgroundColor': '#FFFFFF', 'borderColor': '#6B7280', 'textColor': '#374151',
                'classNames': ['cid-libre'],
                'extendedProps': {'statut': c.statut, 'detail': True, 'agent': nom_agent,
                                  'lieu': c.lieu_affichage, 'peut_reserver': c.peut_etre_reserve_par(user),
                                  'nature': c.get_nature_display()}}

    # Collègue sans accès au détail : gris, « Occupé », nature seulement.
    # Un rendez-vous annulé ou reporté ne l'occupe plus : il n'apparaît pas.
    if not c.voit_le_detail(user):
        if c.statut in STATUTS_ANNULES:
            return None
        return {**base, 'title': f"{icone} Occupé – {'Réunion' if reunion else nom_agent}",
                'backgroundColor': GRIS_OCCUPE, 'borderColor': '#9CA3AF', 'textColor': '#111827',
                'extendedProps': {'statut': 'OCCUPE', 'detail': False, 'agent': nom_agent,
                                  'nature': c.get_nature_display()}}

    clair, plein = COULEURS_DOMAINE.get(c.domaine, COULEURS_DOMAINE['SOCIAL'])
    realise = c.statut in STATUTS_REALISES
    annule = c.statut in STATUTS_ANNULES
    fond = plein if realise else clair
    classes = []
    if annule:
        classes.append('cid-annule')
    if c.statut == 'VAD_ABSENT':
        classes.append('cid-vad-absent')
    usager = f" – {c.beneficiaire.prenom} {c.beneficiaire.nom.upper()}" if c.beneficiaire_id else ""
    if reunion:
        usager = f" – {c.intitule}" if c.intitule else ""
    return {**base,
            'title': f"{icone}{' ★' if c.premiere_fois else ''} {c.get_nature_display()}{usager}",
            'backgroundColor': fond, 'borderColor': plein,
            'textColor': '#FFFFFF' if realise else '#111827',
            'classNames': classes,
            'extendedProps': {
                'statut': c.statut, 'statut_libelle': c.get_statut_display(), 'detail': True,
                'agent': nom_agent, 'nature_code': c.nature, 'nature': c.get_nature_display(),
                'domaine': c.get_domaine_display(), 'lieu': c.lieu_affichage,
                'usager': (f"{c.beneficiaire.prenom} {c.beneficiaire.nom.upper()} ({c.beneficiaire.code_interne})"
                           if c.beneficiaire_id else ""),
                'premiere_fois': c.premiere_fois,
                'description': c.description,
                'est_permanence': c.nature == 'PERMANENCE',
                'peut_modifier': (c.peut_gerer_reunion(user) if reunion
                                  else c.peut_etre_modifie_par(user) or c.est_participant(user)),
                'participants': ", ".join(u.get_full_name() or u.username for u in participants) if reunion else "",
            }}


def evenement_indisponibilite(b):
    """Jour bloqué d'un agent : noir « Indisponible » (le motif n'est pas affiché)."""
    nom = b.agent.get_full_name() or b.agent.username
    return {
        'id': f'indispo-{b.id}', 'title': f"Indisponible – {nom}",
        'start': f"{b.date.isoformat()}T{_heure(b.heure_debut)}",
        'end': f"{b.date.isoformat()}T{_heure(b.heure_fin)}",
        'backgroundColor': NOIR_INDISPONIBLE, 'borderColor': NOIR_INDISPONIBLE, 'textColor': '#FFFFFF',
        'extendedProps': {'type': 'indisponible', 'detail': False},
    }


def rdv_de_la_mds(mds):
    """Tous les rendez-vous d'une MDS, qu'ils soient en salle ou non."""
    return CreneauRdv.objects.filter(Q(mds=mds) | Q(salle__mds=mds))


def est_premiere_fois(beneficiaire, mds, exclure_id=None):
    """
    Vrai si l'usager n'a encore eu AUCUN rendez-vous réalisé avec un agent social de cette MDS.
    Sert à pré-cocher la case « 1er rendez-vous » (l'agent peut corriger).
    """
    if beneficiaire is None or mds is None:
        return False
    deja = (rdv_de_la_mds(mds).filter(beneficiaire=beneficiaire, statut__in=STATUTS_REALISES)
            .exclude(pk=exclure_id).select_related('agent'))
    return not any(r.agent and r.agent.a_la_capacite('peut_instruire') for r in deja)


def conflits_agent(agent, date, debut, fin, exclure_id=None):
    """Rendez-vous ou permanences déjà prévus pour l'agent sur cet horaire (annulés exclus)."""
    return (CreneauRdv.objects
            .filter(Q(agent=agent) | Q(co_intervenants=agent), date=date,
                    heure_debut__lt=fin, heure_fin__gt=debut)
            .exclude(statut__in=STATUTS_ANNULES)
            .exclude(pk=exclure_id).distinct())


# =============================================================================
# DISPONIBILITÉS (lot 2) : qui est libre, d'un coup d'œil, sans aucun détail
# =============================================================================

PAS_MINUTES = 30
HEURE_GRILLE_DEBUT, HEURE_GRILLE_FIN = 8, 18


def _minutes(t):
    return t.hour * 60 + t.minute


def grille_disponibilites(agents, jour):
    """
    Pour chaque agent : une case par demi-heure de 8 h à 18 h, 'libre', 'occupe' ou 'indisponible'.
    Rien d'autre n'est révélé (ni la nature, ni l'usager, ni le motif).
    """
    from .models import JourBloque
    cases = list(range(HEURE_GRILLE_DEBUT * 60, HEURE_GRILLE_FIN * 60, PAS_MINUTES))
    entetes = [f"{m // 60:02d}:{m % 60:02d}" for m in cases]
    fermetures = list(JourBloque.objects.filter(date=jour, agent__isnull=True, salle__isnull=True))
    lignes = []
    for agent in agents:
        occupe = [(_minutes(r.heure_debut), _minutes(r.heure_fin)) for r in
                  CreneauRdv.objects.filter(Q(agent=agent) | Q(co_intervenants=agent), date=jour)
                  .exclude(statut__in=STATUTS_ANNULES).distinct()]
        indispo = [(_minutes(b.heure_debut), _minutes(b.heure_fin)) for b in
                   list(JourBloque.objects.filter(date=jour, agent=agent)) + fermetures]
        etats = []
        for m in cases:
            fin = m + PAS_MINUTES
            if any(d < fin and f > m for d, f in indispo):
                etats.append('indisponible')
            elif any(d < fin and f > m for d, f in occupe):
                etats.append('occupe')
            else:
                etats.append('libre')
        lignes.append({'agent': agent, 'etats': etats})
    return {'entetes': entetes, 'lignes': lignes}


def indisponibilites(agent, jour, debut, fin):
    """Jours bloqués (congés, formation… ou fermeture de la MDS) qui tombent sur l'horaire."""
    from .models import JourBloque
    return JourBloque.objects.filter(Q(agent=agent) | Q(agent__isnull=True, salle__isnull=True),
                                     date=jour, heure_debut__lt=fin, heure_fin__gt=debut)
