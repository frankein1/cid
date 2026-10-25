# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/invitation.py
"""
Invitation d'un partenaire à un rendez-vous (fichier .ics).

CID n'envoie rien : l'agent joint le fichier à un e-mail depuis sa messagerie professionnelle,
et le partenaire clique pour l'ajouter à son agenda (Outlook, Thunderbird, Google…).
L'invitation ne contient NI le nom de l'usager NI le motif : seulement la date, l'heure,
le lieu (si l'agent le souhaite) et la MDS.
"""
from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.utils import timezone

PARIS = ZoneInfo('Europe/Paris')


def nom_mds(rdv):
    mds = rdv.mds or (rdv.salle.mds if rdv.salle_id else None)
    return mds.nom if mds else "la MDS"


def texte_invitation(rdv, avec_lieu=True):
    agent = (rdv.agent.get_full_name() or rdv.agent.username) if rdv.agent else ""
    lignes = [
        f"Rendez-vous avec une famille accompagnée par {nom_mds(rdv)}.",
        f"Date : {rdv.date:%d/%m/%Y}, de {rdv.heure_debut:%H:%M} à {rdv.heure_fin:%H:%M}.",
    ]
    if avec_lieu and rdv.lieu_affichage:
        lignes.append(f"Lieu : {rdv.lieu_affichage}.")
    if agent:
        lignes.append(f"Contact : {agent}{' – ' + rdv.agent.email if rdv.agent.email else ''}.")
    return "\n".join(lignes)


def objet_invitation(rdv):
    return f"Rendez-vous le {rdv.date:%d/%m/%Y} à {rdv.heure_debut:%H:%M} – {nom_mds(rdv)}"


def fichier_ics(rdv, partenaire, avec_lieu=True):
    """Invitation au format iCalendar (méthode REQUEST : le partenaire peut accepter)."""
    return fichier_ics_groupe(rdv, [partenaire], avec_lieu, uid=f"rdv-{rdv.pk}-partenaire-{partenaire.pk}@cid-cd13")


def fichier_ics_groupe(rdv, partenaires, avec_lieu=True, uid=None):
    """Une seule invitation pour tous les partenaires du rendez-vous."""
    from icalendar import Calendar, Event, vCalAddress, vText
    cal = Calendar()
    cal.add('prodid', '-//CID CD13//Agenda MDS//FR')
    cal.add('version', '2.0')
    cal.add('method', 'REQUEST')
    ev = Event()
    ev.add('uid', uid or f"rdv-{rdv.pk}@cid-cd13")
    ev.add('dtstamp', timezone.now())
    # Heures converties en temps universel : tous les agendas les remettent à l'heure locale,
    # sans avoir besoin de la description du fuseau (VTIMEZONE)
    ev.add('dtstart', datetime.combine(rdv.date, rdv.heure_debut, tzinfo=PARIS).astimezone(dt_timezone.utc))
    ev.add('dtend', datetime.combine(rdv.date, rdv.heure_fin, tzinfo=PARIS).astimezone(dt_timezone.utc))
    ev.add('summary', objet_invitation(rdv))
    ev.add('description', texte_invitation(rdv, avec_lieu))
    if avec_lieu and rdv.lieu_affichage:
        ev.add('location', rdv.lieu_affichage)
    if rdv.agent and rdv.agent.email:
        org = vCalAddress(f"MAILTO:{rdv.agent.email}")
        org.params['cn'] = vText(rdv.agent.get_full_name() or rdv.agent.username)
        ev['organizer'] = org
    for partenaire in partenaires:
        if not partenaire.email:
            continue
        att = vCalAddress(f"MAILTO:{partenaire.email}")
        att.params['cn'] = vText(partenaire.contact or partenaire.organisme)
        att.params['role'] = vText('REQ-PARTICIPANT')
        att.params['rsvp'] = vText('TRUE')
        ev.add('attendee', att, encode=0)
    cal.add_component(ev)
    return cal.to_ical()


def brouillon_eml(rdv, partenaires, expediteur, corps, avec_lieu=True):
    """
    Brouillon d'e-mail complet (.eml) : destinataires, objet, texte ET invitation jointe.
    L'en-tête « X-Unsent: 1 » fait qu'Outlook l'ouvre comme un nouveau message prêt à envoyer :
    l'agent relit, puis clique sur Envoyer. CID n'envoie toujours rien lui-même.
    """
    from email.message import EmailMessage
    from email.utils import formataddr
    msg = EmailMessage()
    msg['X-Unsent'] = '1'
    if expediteur.email:
        msg['From'] = formataddr((expediteur.get_full_name() or expediteur.username, expediteur.email))
    msg['To'] = ", ".join(formataddr((p.contact or p.organisme, p.email)) for p in partenaires if p.email)
    msg['Subject'] = objet_invitation(rdv)
    msg.set_content(corps)
    msg.add_attachment(fichier_ics_groupe(rdv, partenaires, avec_lieu), maintype='text', subtype='calendar',
                       filename='invitation.ics', params={'method': 'REQUEST'})
    return msg.as_bytes()
