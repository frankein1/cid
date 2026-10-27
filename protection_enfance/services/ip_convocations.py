# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/services/ip_convocations.py
"""
Auditions et convocations :
  - on fixe la date et l'heure d'une audition (parents : une case par adulte ; enfants : une case par
    enfant, tous au même créneau, reçus un par un) → les courriers de convocation sont produits aussitôt :
    un par adulte convoqué, un pour les enfants adressé à l'adulte chez qui ils vivent ;
  - après l'audition, présence notée pour chacun ;
  - absence : report à l'amiable (nouvelle date convenue, nouveau courrier, pas de non-coopération)
    ou LRAR pour la seule personne absente.
"""
from collections import OrderedDict

from django.db import transaction
from django.utils import timezone

from protection_enfance.models import ActionIP, ConvoqueIP
from protection_enfance.models.m_evaluation import TYPES_AUDITION
from protection_enfance.services.ip_circuit import CircuitError, enregistrer_action, journal, mettre_a_jour_action


def _noms(personnes):
    return ", ".join(f"{p.prenom} {p.nom.upper()}".strip() for p in personnes)


def destinataires_enfants(enfants):
    """Regroupe les enfants par adulte qui les héberge (un courrier par foyer)."""
    groupes = OrderedDict()
    for e in enfants:
        if not e.heberge_par_id:
            raise CircuitError(f"Indiquez chez qui vit {e.prenom} (composition familiale) avant de le convoquer.")
        groupes.setdefault(e.heberge_par, []).append(e)
    return groupes


@transaction.atomic
def programmer_audition(ip, user, type_action, date, duree, adultes=(), enfants=(), professionnels=(),
                        agenda=True, lrar_numeros=None, report_convenu=False, precision=""):
    """
    Crée l'audition (prévue, inscrite à l'agenda), une ligne par personne convoquée et les courriers.
    lrar_numeros : {adulte destinataire: n° de LRAR} pour une relance en recommandé.
    """
    if type_action not in TYPES_AUDITION:
        raise CircuitError("Type d'audition inconnu.")
    adultes, enfants = list(adultes), list(enfants)
    if type_action == 'AUDITION_PARENTS' and not adultes:
        raise CircuitError("Cochez au moins un adulte à convoquer.")
    if type_action == 'AUDITION_ENFANT' and not enfants:
        raise CircuitError("Cochez au moins un enfant à convoquer.")
    groupes = destinataires_enfants(enfants) if enfants else {}
    if lrar_numeros is not None:
        dest = adultes + list(groupes.keys())
        manquants = [d for d in dest if not (lrar_numeros.get(d) or '').strip()]
        if manquants:
            raise CircuitError("Le numéro de la LRAR est obligatoire (preuve de l'envoi).")

    concernes = adultes + enfants
    action = enregistrer_action(ip, user, {
        'type_action': type_action, 'date': date, 'duree_minutes': duree or 60, 'resultat': 'PREVU',
        'personnes': _noms(concernes), 'compte_rendu': precision,
    }, professionnels, agenda=agenda)
    action.adultes_concernes.set(adultes)
    action.enfants_concernes.set(enfants)
    for a in adultes:
        ConvoqueIP.objects.create(action=action, adulte=a)
    for e in enfants:
        ConvoqueIP.objects.create(action=action, enfant=e)

    type_courrier = 'LRAR' if lrar_numeros is not None else 'CONVOCATION'
    courriers = []
    envois = [(a, [a], []) for a in adultes] + [(h, [], groupe) for h, groupe in groupes.items()]
    for destinataire, ads, enfs in envois:
        c = ActionIP.objects.create(
            ip=ip, auteur=user, type_action=type_courrier, date=timezone.now(), duree_minutes=0,
            resultat='REALISE', date_rdv_propose=date, rdv=action, destinataire=destinataire,
            report_convenu=report_convenu, personnes=destinataire.nom_complet,
            numero_lrar=(lrar_numeros or {}).get(destinataire, '').strip()[:40])
        c.adultes_concernes.set(ads)
        c.enfants_concernes.set(enfs)
        c.participants.set(professionnels)
        journal(ip, user, f"{c.get_type_action_display()} à {destinataire.nom_complet}"
                          + (" (date convenue)" if report_convenu else ""),
                f"Pour l'audition du {timezone.localtime(date):%d/%m/%Y à %H:%M}"
                + (f" – enfants : {_noms(enfs)}" if enfs else "")
                + (f" – LRAR n° {c.numero_lrar}" if c.numero_lrar else ""))
        courriers.append(c)
    return action, courriers


@transaction.atomic
def noter_presences(action, user, presences):
    """presences : {ConvoqueIP: (presence, motif)}. Met à jour l'audition et son créneau d'agenda."""
    for cv, (presence, motif) in presences.items():
        if cv.action_id != action.pk or presence not in ('ATTENDU', 'PRESENT', 'ABSENT', 'REPORTE'):
            continue
        if (cv.presence, cv.motif) != (presence, motif):
            cv.presence, cv.motif = presence, motif[:255]
            cv.save(update_fields=['presence', 'motif'])
    etats = set(action.convoques.values_list('presence', flat=True))
    if 'ATTENDU' in etats:
        return
    resultat = 'REALISE' if 'PRESENT' in etats else ('REPORTE' if etats == {'REPORTE'} else 'ABSENT')
    detail = "; ".join(f"{cv.personne} : {cv.get_presence_display().lower()}"
                       + (f" ({cv.motif})" if cv.motif else "") for cv in action.convoques.all())
    # Les présences sont déjà affichées personne par personne : le compte rendu saisi est conservé tel quel
    mettre_a_jour_action(action, user, resultat, action.compte_rendu)
    journal(action.ip, user, f"Présences : {action.get_type_action_display()}", detail)


def _relance(convoques, user, date, lrar_numero=None, motif=""):
    convoques = list(convoques)
    if not convoques:
        raise CircuitError("Aucune personne sélectionnée.")
    action = convoques[0].action
    if date <= timezone.now():
        raise CircuitError("La nouvelle date doit être dans le futur.")
    adultes = [cv.adulte for cv in convoques if cv.adulte_id]
    enfants = [cv.enfant for cv in convoques if cv.enfant_id]
    numeros = None
    if lrar_numero is not None:
        dests = set(adultes) | {e.heberge_par for e in enfants}
        if len(dests) > 1:
            raise CircuitError("Une LRAR par destinataire : relancez chaque foyer séparément.")
        numeros = {d: lrar_numero for d in dests}
    nouvelle, courriers = programmer_audition(
        action.ip, user, action.type_action, date, action.duree_minutes, adultes, enfants,
        list(action.participants.all()), agenda=bool(action.creneau_id), lrar_numeros=numeros,
        report_convenu=lrar_numero is None, precision=motif)
    for cv in convoques:
        cv.suite = nouvelle
        if lrar_numero is None:
            cv.presence, cv.motif = 'REPORTE', (motif or cv.motif)[:255]
        elif cv.presence == 'ATTENDU':
            cv.presence = 'ABSENT'
        cv.save(update_fields=['suite', 'presence', 'motif'])
    noter_presences(action, user, {})
    return nouvelle, courriers


@transaction.atomic
def reporter(convoques, user, date, motif):
    """Absence justifiée : nouvelle date convenue avec la famille (n'est pas une non-coopération)."""
    if not (motif or '').strip():
        raise CircuitError("Indiquez le motif de l'absence et l'accord trouvé avec la famille.")
    return _relance(convoques, user, date, motif=motif)


@transaction.atomic
def relancer_lrar(convoques, user, date, numero):
    """Absence non justifiée : LRAR à la seule personne absente (ou à l'adulte chez qui vit l'enfant)."""
    if not (numero or '').strip():
        raise CircuitError("Le numéro de la LRAR est obligatoire (preuve de l'envoi).")
    return _relance(convoques, user, date, lrar_numero=numero)


def a_relancer(action):
    """
    Personnes sans suite, groupées par adulte destinataire du courrier :
    report à l'amiable possible si attendues ou absentes ; LRAR seulement si toutes sont absentes.
    """
    groupes = OrderedDict()
    for cv in action.convoques.select_related('adulte', 'enfant__heberge_par'):
        if cv.presence in ('ATTENDU', 'ABSENT') and not cv.suite_id:
            groupes.setdefault(cv.destinataire_courrier, []).append(cv)
    return [{'destinataire': d, 'convoques': cvs, 'lrar_possible': all(cv.presence == 'ABSENT' for cv in cvs)}
            for d, cvs in groupes.items()]


def non_cooperants(ip):
    """Personnes restées absentes malgré une LRAR (aide à cocher la non-coopération dans le rapport)."""
    lrar_auditions = ActionIP.objects.filter(ip=ip, type_action='LRAR').values_list('rdv_id', flat=True)
    return [cv for cv in ConvoqueIP.objects.filter(action_id__in=lrar_auditions, presence='ABSENT')
            .select_related('adulte', 'enfant')]
