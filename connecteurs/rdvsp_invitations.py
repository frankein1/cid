# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/rdvsp_invitations.py
"""
RDV-Solidarités, étape 2 : invitations à prendre en ligne le RDV de renouvellement du contrat RSA,
et suspension de la réservation en ligne (docs/RDV_SERVICE_PUBLIC.md).

- Chaque mois (le 1er lundi par défaut, réglable), CID prépare pour chaque référent la liste de ses
  bénéficiaires dont le contrat arrive à échéance ; les usagers suspendus en sont exclus. Le référent est
  prévenu par la messagerie de CID et peut décocher ; sans validation, la liste part telle quelle le
  lendemain soir (réglable).
- L'envoi crée l'usager dans RDV-Solidarités si besoin, obtient son lien personnel de réservation
  (le motif « Renouvellement RSA » n'est réservable que sur invitation), puis envoie un courriel avec le
  courrier joint (QR code) ; sans adresse courriel, le courrier est à imprimer.
- Suspension : une case de la fiche usager, décidée par l'agent ; CID affiche à côté les annulations
  tardives (moins de 48 h avant) et les absences, sans rien bloquer de lui-même.
"""
import logging
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone

from . import rdv_service_public as api
from . import rdvsp_synchro as sync
from .models import (CampagneInvitations, InvitationRSA, LienUsagerRDVSP, MdsRDVSP, MotifRDVSP, ParametresRDVSP,
                     RdvRDVSP, ReservationEnLigne)

logger = logging.getLogger(__name__)

ANNULATION_TARDIVE_HEURES = 48


# --- Suspension et incidents ----------------------------------------------------
def est_suspendu(beneficiaire):
    return ReservationEnLigne.objects.filter(beneficiaire=beneficiaire, suspendue=True).exists()


def incidents(beneficiaire):
    """Annulations à moins de 48 h et absences sur les RDV venus de RDV-Solidarités."""
    tardives, absences = [], []
    for r in RdvRDVSP.objects.filter(beneficiaire=beneficiaire).select_related("creneau").order_by("-debut"):
        if r.annule_le and r.statut_sp == "excused" and r.debut - r.annule_le < timedelta(hours=ANNULATION_TARDIVE_HEURES):
            tardives.append(r)
        elif r.statut_sp == "noshow" or (r.creneau and r.creneau.statut == "ABSENT"):
            absences.append(r)
    return {"annulations_tardives": tardives, "absences": absences,
            "a_examiner": len(tardives) >= 2 or len(absences) >= 1}


def suspendre(beneficiaire, user, suspendue, commentaire=""):
    r, _ = ReservationEnLigne.objects.get_or_create(beneficiaire=beneficiaire)
    r.suspendue, r.commentaire, r.modifiee_par = suspendue, commentaire[:255], user
    r.save()
    return r


# --- Calendrier --------------------------------------------------------------------
def jour_preparation(mois):
    p = ParametresRDVSP.get()
    premier = mois.replace(day=1)
    return premier + timedelta(days=(p.jour_preparation - premier.weekday()) % 7)


def envoi_prevu(mois):
    p = ParametresRDVSP.get()
    jour = jour_preparation(mois) + timedelta(days=p.jours_avant_envoi)
    heure = p.heure_envoi if not isinstance(p.heure_envoi, str) else datetime.strptime(p.heure_envoi, "%H:%M").time()
    return timezone.make_aware(datetime.combine(jour, heure))


# --- Préparation ----------------------------------------------------------------------
def contrats_a_renouveler():
    """Mêmes règles que la vue « À renouveler » des contrats (insertion/views_contrats.py)."""
    from insertion.models import ContratInsertion
    from insertion.views_contrats import _filtrer
    return (_filtrer(ContratInsertion.objects.all(), "a_renouveler")
            .select_related("beneficiaire", "referent", "mds").order_by("beneficiaire_id", "-date_fin"))


@transaction.atomic
def preparer(mois=None, prevenir=True):
    """Prépare la campagne du mois (une seule fois). Renvoie (campagne, créée ?)."""
    mois = (mois or timezone.localdate()).replace(day=1)
    campagne, cree = CampagneInvitations.objects.get_or_create(mois=mois, defaults={"envoi_prevu": envoi_prevu(mois)})
    if not cree:
        return campagne, False
    mds_en_ligne = set(MdsRDVSP.objects.filter(en_ligne=True).values_list("mds_id", flat=True))
    suspendus = set(ReservationEnLigne.objects.filter(suspendue=True).values_list("beneficiaire_id", flat=True))
    vus = set()
    for c in contrats_a_renouveler():
        b = c.beneficiaire
        if b.pk in vus or b.pk in suspendus or (c.mds_id or b.mds_id) not in mds_en_ligne:
            continue
        vus.add(b.pk)
        InvitationRSA.objects.create(campagne=campagne, beneficiaire=b, contrat=c, referent=c.referent)
    if prevenir:
        transaction.on_commit(lambda: prevenir_referents(campagne))
    return campagne, True


def prevenir_referents(campagne):
    from django.urls import reverse
    from messagerie.models import Message, StatutLecture
    lien = reverse("connecteurs:invitations_rsa")
    from django.contrib.auth import get_user_model
    expediteur = ParametresRDVSP.get().compte_synchro or get_user_model().objects.filter(is_superuser=True).first()
    if expediteur is None:
        return
    for ref in {i.referent for i in campagne.invitations.select_related("referent") if i.referent}:
        n = campagne.invitations.filter(referent=ref).count()
        msg = Message.objects.create(
            expediteur=expediteur, destinataire=ref, objet=f"Invitations RSA de {campagne.mois:%m/%Y} à valider ({n})",
            contenu=(f"{n} de vos bénéficiaires ont un contrat qui arrive à échéance. CID leur proposera de "
                     f"prendre en ligne leur rendez-vous de renouvellement.\n\nDécochez ceux à ne pas inviter : "
                     f"{lien}\nSans validation, la liste partira telle quelle le "
                     f"{timezone.localtime(campagne.envoi_prevu):%d/%m/%Y à %H:%M}.\n\nMessage automatique de CID."),
            motif='suivi_dossier', priorite='normale')
        StatutLecture.objects.create(message=msg, utilisateur=ref, type_reception='destinataire')


def valider(referent, campagne, ids_cochees):
    """Le référent garde les cases cochées ; les autres ne seront pas invitées ce mois-ci."""
    maintenant = timezone.now()
    for inv in campagne.invitations.filter(referent=referent, envoyee_le__isnull=True):
        inv.cochee = inv.pk in ids_cochees
        inv.validee_le = maintenant
        inv.save(update_fields=["cochee", "validee_le"])


# --- Envoi ---------------------------------------------------------------------------------
def courriel_reel():
    return settings.EMAIL_BACKEND.endswith("smtp.EmailBackend")


def _lien(usager_sp_id, mds_sp, jeton):
    conf = api.configuration()
    params = [("invitation_token", jeton), ("organisation_ids[]", mds_sp.organisation_sp_id)]
    if mds_sp.lieu_sp_id:
        params.append(("lieu_id", mds_sp.lieu_sp_id))
    return f"{conf['url']}/prendre_rdv?{urlencode(params)}"


def _usager_sp(c, b, mds_sp):
    lien = LienUsagerRDVSP.objects.filter(beneficiaire=b).first()
    if lien:
        return lien.usager_rdvsp_id
    corps = {**api._usager(b), "organisation_ids": [mds_sp.organisation_sp_id]}
    u = c.appel("POST", "/users", json=corps)
    u = u.get("user") if isinstance(u.get("user"), dict) else u
    LienUsagerRDVSP.objects.create(beneficiaire=b, usager_rdvsp_id=str(u["id"]))
    return str(u["id"])


def envoyer(inv, c=None):
    """Obtient le lien personnel, puis envoie le courriel (courrier joint) ou prépare le courrier à imprimer."""
    from .invitation_pdf import courrier_invitation_pdf
    b = inv.beneficiaire
    mds_sp = MdsRDVSP.objects.filter(mds_id=(inv.contrat.mds_id if inv.contrat and inv.contrat.mds_id else b.mds_id)).first()
    if mds_sp is None:
        raise sync.SynchroErreur("MDS non reliée à RDV-Solidarités.")
    c = c or sync.client()
    usager = _usager_sp(c, b, mds_sp)
    jeton = c.appel("POST", f"/users/{usager}/rdv_invitation_token").get("invitation_token")
    if not jeton:
        raise sync.SynchroErreur("Lien d'invitation non délivré.")
    inv.lien = _lien(usager, mds_sp, jeton)
    pdf = courrier_invitation_pdf(inv).getvalue()
    if b.email:
        motif = MotifRDVSP.objects.filter(actif=True).first()
        m = EmailMessage(
            subject="Renouvellement de votre contrat RSA : prenez rendez-vous en ligne",
            body=(f"Bonjour,\n\nVotre contrat arrive à échéance. Pour préparer son renouvellement, vous pouvez "
                  f"choisir vous-même votre rendez-vous à la {mds_sp.mds.nom} :\n\n{inv.lien}\n\n"
                  f"Le rendez-vous se réserve au moins {motif.delai_min_heures if motif else 48} heures et au plus "
                  f"{motif.delai_max_jours if motif else 15} jours à l'avance. Ce lien vous est personnel.\n\n"
                  f"Le courrier joint reprend ces informations.\n\n{mds_sp.mds.nom}"),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None), to=[b.email])
        m.attach(f"invitation_rdv_{b.code_interne}.pdf", pdf, "application/pdf")
        m.send()
        inv.mode, inv.courriel_reel = InvitationRSA.COURRIEL, courriel_reel()
    else:
        inv.mode = InvitationRSA.COURRIER
    inv.envoyee_le, inv.erreur = timezone.now(), ""
    inv.save(update_fields=["lien", "mode", "courriel_reel", "envoyee_le", "erreur"])
    return inv


def envoyer_campagne(campagne, maintenant=None):
    """Envoie les invitations cochées et pas encore parties (relançable sans doublon)."""
    c = sync.client()
    bilan = {"courriels": 0, "courriers": 0, "erreurs": 0}
    for inv in campagne.invitations.filter(cochee=True, envoyee_le__isnull=True).select_related(
            "beneficiaire", "contrat", "referent"):
        if est_suspendu(inv.beneficiaire):        # suspendu entre la préparation et l'envoi
            inv.cochee = False
            inv.save(update_fields=["cochee"])
            continue
        try:
            envoyer(inv, c)
            bilan["courriels" if inv.mode == InvitationRSA.COURRIEL else "courriers"] += 1
        except Exception as e:
            logger.exception("rdvsp: invitation non envoyée")
            inv.erreur = f"{type(e).__name__} : {e}"[:300]
            inv.save(update_fields=["erreur"])
            bilan["erreurs"] += 1
    if not campagne.invitations.filter(cochee=True, envoyee_le__isnull=True, erreur="").exists():
        campagne.envoyee_le = maintenant or timezone.now()
        campagne.save(update_fields=["envoyee_le"])
    return bilan


def traiter(maintenant=None):
    """À lancer régulièrement (connexion, commande synchro_rdvsp) : prépare puis envoie quand c'est l'heure."""
    if not sync.prete():
        return None
    maintenant = maintenant or timezone.now()
    jour = timezone.localtime(maintenant).date()
    res = {}
    if jour >= jour_preparation(jour):
        _, res["preparee"] = preparer(jour)
    for campagne in CampagneInvitations.objects.filter(envoyee_le__isnull=True, envoi_prevu__lte=maintenant):
        res[str(campagne)] = envoyer_campagne(campagne, maintenant)
    return res


def a_traiter(maintenant=None):
    """Test rapide (sans appel extérieur) : y a-t-il une campagne à préparer ou à envoyer ?"""
    maintenant = maintenant or timezone.now()
    jour = timezone.localtime(maintenant).date()
    if jour >= jour_preparation(jour) and not CampagneInvitations.objects.filter(mois=jour.replace(day=1)).exists():
        return True
    return CampagneInvitations.objects.filter(envoyee_le__isnull=True, envoi_prevu__lte=maintenant).exists()
