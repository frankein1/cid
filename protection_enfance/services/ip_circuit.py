# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/services/ip_circuit.py
"""
Circuit d'une IP : chaque étape est journalisée et les personnes concernées reçoivent un message CID
(copies : binôme, cadre de la MDS, inspecteur, CRIP). Les messages ne sont PAS rattachés au dossier
de la famille, pour que seules les personnes habilitées sachent qu'une IP existe.
"""
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from protection_enfance.models import (ActionIP, HistoriqueAction, InformationPreoccupante, RapportIP,
                                       SaisineIP)
from protection_enfance.models.m_evaluation import TYPES_AGENDA
from protection_enfance.models.m_ip import CAP_EVALUER, STATUTS_OUVERTS, cadre_ip


class CircuitError(Exception):
    """Étape impossible (ordre du circuit, droits) : le message est affiché tel quel."""


# =============================================================================
# TRACE ET MESSAGES
# =============================================================================

def nom(u):
    return (u.get_full_name() or u.username) if u else "-"


def journal(ip, user, action, commentaire=""):
    return HistoriqueAction.objects.create(information=ip, action=action[:200], user=user, commentaire=commentaire)


def _envoyer(expediteur, destinataire, ip, objet, contenu, priorite='importante'):
    from django.contrib.contenttypes.models import ContentType
    from messagerie.models import Message, StatutLecture
    msg = Message.objects.create(
        expediteur=expediteur, destinataire=destinataire, beneficiaire=None,   # confidentialité de l'IP
        objet=objet[:255], contenu=contenu, motif='suivi_dossier', priorite=priorite,
        content_type=ContentType.objects.get_for_model(ip), object_id=ip.pk, reference=ip.numero,
    )
    StatutLecture.objects.create(message=msg, utilisateur=destinataire, type_reception='destinataire')
    return msg


def diffuser(expediteur, destinataires, ip, objet, contenu, priorite='importante'):
    """Un message par destinataire (sans doublon, jamais à soi-même) ; trace dans le journal."""
    vus = []
    for d in destinataires:
        if d is None or not d.is_active or (expediteur and d.pk == expediteur.pk) or d.pk in [v.pk for v in vus]:
            continue
        _envoyer(expediteur, d, ip, objet, contenu + "\n\nMessage automatique de CID.", priorite)
        vus.append(d)
    if vus:
        journal(ip, expediteur, f"Message : {objet}", "Destinataires : " + ", ".join(nom(v) for v in vus))
    return vus


def inspecteurs():
    from core.models import User
    return list(User.objects.filter(is_active=True, profils__code='PIEF', profils__actif=True).distinct())


def agents_crip():
    from core.models import User
    return list(User.objects.filter(is_active=True, profils__code='CRIP', profils__actif=True).distinct())


def equipe(ip):
    """Binôme + cadre de la MDS en charge (+ cadres des MDS associées)."""
    gens = list(ip.binome) + [cadre_ip(ip.mds)]
    gens += [cadre_ip(m) for m in ip.mds_partage.all()]
    return gens


def _entete(ip):
    return f"IP {ip.numero} – {ip.libelle_famille} ({ip.mds or 'MDS à désigner'})"


# =============================================================================
# 1. CRIP → MDS
# =============================================================================

@transaction.atomic
def transmettre_mds(ip, user):
    if ip.statut != 'RECUE':
        raise CircuitError("Cette IP a déjà été transmise.")
    if not ip.mds:
        raise CircuitError("Choisissez la MDS en charge avant de transmettre.")
    if not ip.enfants.exists():
        raise CircuitError("Indiquez au moins un enfant concerné.")
    ip.statut, ip.date_transmission_mds = 'TRANSMISE_MDS', timezone.now()
    ip.save(update_fields=['statut', 'date_transmission_mds', 'date_modification'])
    journal(ip, user, "Transmise à la MDS", str(ip.mds))
    urgent = ip.niveau_urgence == 'IMMEDIATE'
    diffuser(user, [cadre_ip(ip.mds)] + [cadre_ip(m) for m in ip.mds_partage.all()], ip,
             ("URGENT – " if urgent else "") + f"Nouvelle IP à évaluer : {_entete(ip)}",
             f"La CRIP a transmis l'information préoccupante {ip.numero} à {ip.mds}.\n"
             f"Reçue par la CRIP le {ip.date_reception_crip:%d/%m/%Y} – urgence : {ip.get_niveau_urgence_display()}.\n"
             f"Point intermédiaire : {ip.date_intermediaire:%d/%m/%Y} – échéance : {ip.date_echeance:%d/%m/%Y}.\n\n"
             f"Prochaine étape : programmer la réunion IP et désigner le binôme.",
             'urgente' if urgent else 'importante')


# =============================================================================
# 2. RÉUNION IP ET BINÔME
# =============================================================================

def charge(user):
    """Nombre d'IP ouvertes dont l'agent fait partie du binôme."""
    return InformationPreoccupante.objects.filter(
        Q(binome_1=user) | Q(binome_2=user), statut__in=STATUTS_OUVERTS).count()


def pmi_conseillee(ip):
    return bool(ip.situation_particuliere.strip()) or any(e.releve_pmi for e in ip.enfants.all())


def proposer_binome(ip):
    """
    CID propose ; le cadre décide. Retourne les TS et les professionnels de PMI de la MDS,
    du moins chargé au plus chargé, et une proposition de binôme.
    """
    from core.models import User
    base = (User.objects.filter(is_active=True, profils_mds__mds=ip.mds, profils_mds__actif=True)
            .distinct())
    def classer(codes):
        gens = [u for u in base.filter(profils__code__in=codes, profils__actif=True).distinct()
                if u.a_la_capacite(CAP_EVALUER)]
        return sorted(((u, charge(u)) for u in gens), key=lambda x: (x[1], x[0].last_name))
    ts = classer(['MDS_AGENTS_SOCIAUX'])
    pmi = classer(['MDS_PMI_INFANTILE', 'MDS_PMI_MATERNELLE'])
    conseil_pmi = pmi_conseillee(ip)
    proposition = [x[0] for x in ts[:1]]
    if conseil_pmi and pmi:
        proposition.append(pmi[0][0])
    elif len(ts) > 1:
        proposition.append(ts[1][0])
    return {'ts': ts, 'pmi': pmi, 'pmi_conseillee': conseil_pmi, 'proposition': proposition}


@transaction.atomic
def designer_binome(ip, u1, u2, cadre):
    if ip.statut not in ('TRANSMISE_MDS', 'EN_EVALUATION'):
        raise CircuitError("Le binôme se désigne après réception de l'IP et avant le rapport.")
    if not u1 or not u2 or u1 == u2:
        raise CircuitError("Le binôme compte deux professionnels différents.")
    ancien = list(ip.binome)
    ip.binome_1, ip.binome_2 = u1, u2
    ip.binome_valide_par, ip.date_binome = cadre, timezone.now()
    ip.statut = 'EN_EVALUATION'
    ip.save()
    journal(ip, cadre, "Binôme désigné" if not ancien else "Binôme modifié", f"{nom(u1)} et {nom(u2)}")
    diffuser(cadre, [u1, u2], ip, f"Vous êtes désigné(e) pour l'évaluation : {_entete(ip)}",
             f"{nom(cadre)} vous a désigné(e) avec {nom(u2)} et {nom(u1)} pour évaluer l'IP {ip.numero}.\n"
             f"Échéance : {ip.date_echeance:%d/%m/%Y} (point intermédiaire le {ip.date_intermediaire:%d/%m/%Y}).\n"
             f"Première étape : prendre connaissance du dossier et envoyer les convocations.")


# =============================================================================
# 3. ACTIONS D'ÉVALUATION (tout est enregistré)
# =============================================================================

def _creneau_agenda(action, user):
    """Une réunion, un rendez-vous, une audition ou une VAD prend place dans l'agenda (domaine IP)."""
    from planning.models import CreneauRdv, HistoriqueCreneau
    nature = TYPES_AGENDA.get(action.type_action)
    if not nature:
        return None
    debut = timezone.localtime(action.date)
    fin = debut + timedelta(minutes=action.duree_minutes or 60)
    participants = list(action.participants.all())
    creneau = CreneauRdv.objects.create(
        salle=None, mds=action.ip.mds, agent=participants[0] if participants and nature != 'REUNION' else None,
        date=debut.date(), heure_debut=debut.time(), heure_fin=fin.time(),
        duree_minutes=action.duree_minutes or 60, nature=nature, domaine='IP', type_rdv='IP',
        modalite='VAD' if nature == 'VAD' else 'MDS', beneficiaire=action.ip.famille,
        description=f"IP {action.ip.numero} – {action.get_type_action_display()}",
        statut='RESERVE', cree_par=user,
    )
    creneau.co_intervenants.set(participants)
    HistoriqueCreneau.objects.create(creneau=creneau, action='CREATION', utilisateur=user,
                                     commentaire=f"Depuis l'IP {action.ip.numero}")
    return creneau


@transaction.atomic
def enregistrer_action(ip, user, cleaned, participants=(), agenda=True):
    action = ActionIP.objects.create(ip=ip, auteur=user, **cleaned)
    action.participants.set(participants)
    if agenda and action.resultat in ('PREVU', 'REALISE'):
        action.creneau = _creneau_agenda(action, user)
        if action.creneau:
            action.save(update_fields=['creneau'])
    journal(ip, user, f"{action.get_type_action_display()} ({action.get_resultat_display().lower()})",
            f"{timezone.localtime(action.date):%d/%m/%Y %H:%M}"
            + (f" – LRAR n° {action.numero_lrar}" if action.numero_lrar else "")
            + (f" – {action.personnes}" if action.personnes else ""))
    # Les invitations aux réunions partent aux professionnels concernés
    if action.type_action in ('REUNION_IP', 'POINT_ETAPE', 'REUNION_SYNTHESE') and action.resultat == 'PREVU':
        diffuser(user, participants, ip, f"{action.get_type_action_display()} – {_entete(ip)}",
                 f"{action.get_type_action_display()} le {timezone.localtime(action.date):%d/%m/%Y à %H:%M}"
                 f" ({action.duree_minutes} min). Le créneau est inscrit dans votre agenda.")
    return action


@transaction.atomic
def mettre_a_jour_action(action, user, resultat, compte_rendu, date_accuse_reception=None):
    ancien = action.get_resultat_display()
    action.resultat, action.compte_rendu = resultat, compte_rendu
    if date_accuse_reception:
        action.date_accuse_reception = date_accuse_reception
    action.save()
    if action.creneau_id:
        statut = {'REALISE': 'VENU_RECU', 'ABSENT': 'VAD_ABSENT' if action.type_action == 'VAD' else 'ABSENT',
                  'ANNULE': 'ANNULE_MDS', 'REPORTE': 'REPORT_MDS'}.get(resultat)
        if statut:
            action.creneau.statut = statut
            action.creneau.save(update_fields=['statut'])
    journal(action.ip, user, f"{action.get_type_action_display()} : {ancien} → {action.get_resultat_display()}",
            compte_rendu[:500])


# =============================================================================
# 4. RAPPORT, SYNTHÈSE, VISAS
# =============================================================================

def rapport_de(ip):
    rapport, _ = RapportIP.objects.get_or_create(ip=ip)
    return rapport


@transaction.atomic
def soumettre_rapport(ip, user):
    rapport = rapport_de(ip)
    if ip.statut != 'EN_EVALUATION':
        raise CircuitError("Le rapport se soumet pendant l'évaluation.")
    if not rapport.complet:
        raise CircuitError("Renseignez au moins l'analyse et la préconisation avant de soumettre le rapport.")
    rapport.date_soumission, rapport.redige_par = timezone.now(), user
    rapport.save()
    ip.statut = 'SYNTHESE'
    ip.save(update_fields=['statut', 'date_modification'])
    journal(ip, user, "Rapport soumis en synthèse", rapport.get_preconisation_display())
    diffuser(user, equipe(ip), ip, f"Rapport prêt pour la synthèse : {_entete(ip)}",
             f"{nom(user)} a soumis le rapport de l'IP {ip.numero} (préconisation : "
             f"{rapport.get_preconisation_display()}).\nÀ voir en réunion de synthèse, puis visas du cadre et de l'AS.")


@transaction.atomic
def renvoyer_en_redaction(ip, user, motif):
    if ip.statut != 'SYNTHESE':
        raise CircuitError("Seul un rapport en synthèse peut être renvoyé en rédaction.")
    rapport = rapport_de(ip)
    rapport.date_soumission = None
    rapport.visa_cadre_par = rapport.visa_as_par = None
    rapport.date_visa_cadre = rapport.date_visa_as = None
    rapport.save()
    ip.statut = 'EN_EVALUATION'
    ip.save(update_fields=['statut', 'date_modification'])
    journal(ip, user, "Rapport renvoyé en rédaction", motif)
    diffuser(user, equipe(ip), ip, f"Rapport à reprendre : {_entete(ip)}", f"Motif : {motif}")


@transaction.atomic
def viser(ip, user, role, date_synthese=None):
    """role = 'cadre' ou 'as'. Les deux visas + la date de synthèse envoient le rapport à l'inspecteur."""
    if ip.statut != 'SYNTHESE':
        raise CircuitError("Le rapport n'est pas en synthèse.")
    rapport = rapport_de(ip)
    if date_synthese:
        rapport.date_synthese = date_synthese
    if role == 'cadre':
        if not ip.peut_piloter(user):
            raise CircuitError("Visa réservé au cadre de la MDS.")
        rapport.visa_cadre_par, rapport.date_visa_cadre = user, timezone.now()
    elif role == 'as':
        if not ip.est_binome(user):
            raise CircuitError("Visa réservé à un membre du binôme.")
        rapport.visa_as_par, rapport.date_visa_as = user, timezone.now()
    else:
        raise CircuitError("Visa inconnu.")
    rapport.save()
    journal(ip, user, f"Visa {'du cadre' if role == 'cadre' else 'de l’AS'} sur le rapport",
            f"Synthèse du {rapport.date_synthese:%d/%m/%Y}" if rapport.date_synthese else "")
    if rapport.visa_cadre_par and rapport.visa_as_par:
        if not rapport.date_synthese:
            raise CircuitError("Indiquez la date de la réunion de synthèse.")
        transmettre_pief(ip, user)


def transmettre_pief(ip, user):
    ip.statut, ip.date_transmission_pief = 'TRANSMISE_PIEF', timezone.now()
    ip.save(update_fields=['statut', 'date_transmission_pief', 'date_modification'])
    retard = ip.depassement_jours
    journal(ip, user, "Rapport transmis à l'inspecteur enfance famille",
            "Dans le délai de 3 mois" if not retard else f"Hors délai : {retard} jour(s) de dépassement")
    rapport = rapport_de(ip)
    diffuser(user, inspecteurs() + equipe(ip), ip, f"Rapport d'évaluation à viser : {_entete(ip)}",
             f"Le rapport de l'IP {ip.numero}, vu en synthèse le {rapport.date_synthese:%d/%m/%Y}, est transmis à "
             f"l'inspecteur enfance famille.\nPréconisation : {rapport.get_preconisation_display()}.\n"
             f"Visas : {nom(rapport.visa_cadre_par)} (cadre), {nom(rapport.visa_as_par)} (AS).\n"
             + ("Délai de 3 mois respecté." if not retard else f"Délai dépassé de {retard} jour(s)."))


# =============================================================================
# 5. INSPECTEUR : CONTRESEING, AUTRE SUITE OU COMPLÉMENT
# =============================================================================

@transaction.atomic
def avis_inspecteur(ip, user, avis, decision, commentaire):
    if ip.statut != 'TRANSMISE_PIEF':
        raise CircuitError("Le rapport n'attend pas l'avis de l'inspecteur.")
    rapport = rapport_de(ip)
    rapport.avis_pief, rapport.commentaire_pief = avis, commentaire
    rapport.visa_pief_par, rapport.date_visa_pief = user, timezone.now()
    rapport.save()
    ip.inspecteur = user
    if avis == 'COMPLEMENT':
        rapport.date_soumission = None
        rapport.visa_cadre_par = rapport.visa_as_par = None
        rapport.date_visa_cadre = rapport.date_visa_as = None
        rapport.save()
        ip.statut, ip.date_transmission_pief = 'EN_EVALUATION', None
        ip.save()
        journal(ip, user, "Complément d'évaluation demandé par l'inspecteur", commentaire)
        objet = f"Complément d'évaluation demandé : {_entete(ip)}"
    else:
        ip.decision_finale, ip.decision_commentaire = decision, commentaire
        ip.statut, ip.date_cloture = 'CLOTUREE', timezone.now()
        ip.save()
        journal(ip, user, f"Décision de l'inspecteur : {ip.get_decision_finale_display()}", commentaire)
        objet = f"Décision de l'inspecteur : {_entete(ip)}"
    diffuser(user, equipe(ip) + [ip.recue_par], ip, objet,
             f"{nom(user)} (inspecteur enfance famille) : {rapport.get_avis_pief_display()}.\n"
             + (f"Décision : {ip.get_decision_finale_display()}.\n" if ip.decision_finale else "")
             + (f"Commentaire : {commentaire}\n" if commentaire else ""))


# =============================================================================
# SAISINE DU PROCUREUR (à tout moment : proposition → cadre → inspecteur)
# =============================================================================

@transaction.atomic
def proposer_saisine(ip, user, motif, danger_imminent):
    if ip.statut not in ('TRANSMISE_MDS', 'EN_EVALUATION', 'SYNTHESE'):
        raise CircuitError("La saisine se propose pendant l'évaluation.")
    s = SaisineIP.objects.create(ip=ip, motif=motif, danger_imminent=danger_imminent, propose_par=user)
    journal(ip, user, "Saisine du procureur proposée au cadre", motif[:500])
    diffuser(user, equipe(ip), ip, ("URGENT – " if danger_imminent else "") + f"Saisine du procureur proposée : {_entete(ip)}",
             f"{nom(user)} propose de saisir le procureur.\nMotif : {motif}",
             'urgente' if danger_imminent else 'importante')
    return s


@transaction.atomic
def decision_cadre_saisine(s, user, choix, commentaire):
    """choix : 'REFUSER', 'DEMANDER_PIEF' ou 'SAISIR' (danger imminent : saisine directe, inspecteur informé)."""
    if s.statut != 'PROPOSEE':
        raise CircuitError("Cette proposition a déjà été traitée.")
    s.cadre, s.date_decision_cadre, s.commentaire_cadre = user, timezone.now(), commentaire
    ip = s.ip
    if choix == 'REFUSER':
        s.statut = 'REFUSEE_CADRE'
        texte = "n'est pas retenue par le cadre"
        dest = equipe(ip)
    elif choix == 'DEMANDER_PIEF':
        s.statut = 'TRANSMISE_PIEF'
        texte = "est demandée à l'inspecteur enfance famille"
        dest = inspecteurs() + equipe(ip)
    elif choix == 'SAISIR':
        s.statut, s.saisie_directe, s.date_saisine = 'EFFECTUEE', True, timezone.now()
        texte = "est faite directement par le cadre (danger grave et imminent) ; l'inspecteur en est informé"
        dest = inspecteurs() + equipe(ip) + [ip.recue_par]
    else:
        raise CircuitError("Choix inconnu.")
    s.save()
    journal(ip, user, f"Saisine du procureur : {s.get_statut_display()}", commentaire)
    diffuser(user, dest, ip, f"Saisine du procureur – {s.get_statut_display()} : {_entete(ip)}",
             f"La saisine du procureur proposée par {nom(s.propose_par)} {texte}.\nMotif : {s.motif}\n"
             + (f"Commentaire : {commentaire}\n" if commentaire else ""),
             'urgente' if s.danger_imminent or choix == 'SAISIR' else 'importante')


@transaction.atomic
def decision_pief_saisine(s, user, valide, commentaire):
    if s.statut != 'TRANSMISE_PIEF':
        raise CircuitError("Cette saisine n'attend pas l'avis de l'inspecteur.")
    s.inspecteur, s.date_decision_pief, s.commentaire_pief = user, timezone.now(), commentaire
    s.statut = 'VALIDEE_PIEF' if valide else 'REFUSEE_PIEF'
    s.save()
    journal(s.ip, user, f"Saisine du procureur : {s.get_statut_display()}", commentaire)
    diffuser(user, equipe(s.ip), s.ip, f"Saisine du procureur – {s.get_statut_display()} : {_entete(s.ip)}",
             f"{nom(user)} (inspecteur) : {s.get_statut_display().lower()}.\n"
             + (f"Commentaire : {commentaire}\n" if commentaire else "")
             + ("Le courrier de saisine peut être imprimé depuis la fiche IP ; enregistrez ensuite la date d'envoi."
                if valide else ""))


@transaction.atomic
def saisine_effectuee(s, user, date, reference):
    if s.statut != 'VALIDEE_PIEF':
        raise CircuitError("La saisine doit d'abord être validée par l'inspecteur.")
    s.statut, s.date_saisine, s.reference_parquet = 'EFFECTUEE', date or timezone.now(), reference
    s.save()
    journal(s.ip, user, "Procureur saisi", reference)
    diffuser(user, inspecteurs() + equipe(s.ip) + [s.ip.recue_par], s.ip, f"Procureur saisi : {_entete(s.ip)}",
             f"Le procureur a été saisi le {timezone.localtime(s.date_saisine):%d/%m/%Y}."
             + (f" Référence : {reference}." if reference else ""))


# =============================================================================
# RAPPELS (point intermédiaire, échéance)
# =============================================================================

def _expediteur_rappel(ip):
    """Les rappels partent au nom de l'agent CRIP qui a enregistré l'IP (c'est lui qui suit le délai)."""
    return ip.recue_par or ip.cree_par or cadre_ip(ip.mds)


def envoyer_rappels(qs=None):
    """
    Appelé à l'ouverture des listes IP (et par la commande « rappels_ip ») : prévient une seule fois
    le cadre et le binôme au point intermédiaire, puis à l'échéance dépassée.
    """
    aujourdhui = timezone.localdate()
    qs = (qs if qs is not None else InformationPreoccupante.objects.all()).filter(
        statut__in=('TRANSMISE_MDS', 'EN_EVALUATION'))
    n = 0
    for ip in qs.filter(rappel_intermediaire_envoye=False, date_intermediaire__lte=aujourdhui):
        ip.rappel_intermediaire_envoye = True
        ip.save(update_fields=['rappel_intermediaire_envoye'])
        diffuser(_expediteur_rappel(ip), equipe(ip), ip, f"Point intermédiaire atteint : {_entete(ip)}",
                 f"Le point intermédiaire de l'IP {ip.numero} est atteint : il reste {ip.jours_restants} jour(s) "
                 f"avant l'échéance du {ip.date_echeance:%d/%m/%Y}.\n"
                 f"Une réunion de point d'étape peut être programmée depuis la fiche IP (faire le point, entendre "
                 f"un partenaire).")
        n += 1
    for ip in qs.filter(rappel_echeance_envoye=False, date_echeance__lt=aujourdhui):
        ip.rappel_echeance_envoye = True
        ip.save(update_fields=['rappel_echeance_envoye'])
        diffuser(_expediteur_rappel(ip), equipe(ip), ip, f"Échéance dépassée : {_entete(ip)}",
                 f"Le délai de 3 mois de l'IP {ip.numero} est dépassé depuis le {ip.date_echeance:%d/%m/%Y}.",
                 'urgente')
        n += 1
    return n
