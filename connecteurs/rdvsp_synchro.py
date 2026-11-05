# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/rdvsp_synchro.py
"""
Synchronisation des agendas CID ↔ RDV-Solidarités, étape 1 (docs/RDV_SERVICE_PUBLIC.md).

CID est l'agenda maître ; RDV-Solidarités n'est que la vitrine de réservation en ligne.
1. Publication : chaque demi-journée de réception (en MDS, MDS ouverte en ligne) devient une permanence
   hebdomadaire dans RDV-Solidarités, publiée pour N semaines puis renouvelée. Une demi-journée retirée
   ou modifiée dans CID est neutralisée là-bas par une absence (l'API ne permet pas d'effacer une permanence).
2. Blocages : un créneau pris dans CID, un jour bloqué, ou le plafond de RDV en ligne atteint dans une
   demi-journée → une absence dans RDV-Solidarités ; elle est retirée quand le motif disparaît.
3. Retour : chaque RDV pris, modifié ou annulé dans RDV-Solidarités arrive par un avis signé et est
   reporté dans l'agenda CID (créneau réservé, rattaché à l'usager s'il est connu).
4. Statuts : « venu » / « absent » saisis dans CID sont renvoyés à RDV-Solidarités.

Tout passe par le compte de synchronisation (ParametresRDVSP.compte_synchro). Les erreurs n'interrompent
jamais le travail des agents : elles sont tracées (AppelRDVSP, AvisRDVSP) et visibles sur la page d'état.
Vérifié contre une vraie copie de RDV-Solidarités : .github/workflows/essai-rdv-solidarites.yml.
"""
import hashlib
import hmac
import json
import logging
import os
from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from . import rdv_service_public as api
from .models import (AbsenceRDVSP, AppelRDVSP, AvisRDVSP, LienUsagerRDVSP, MdsRDVSP, MotifRDVSP,
                     MotifRDVSPPublie, ParametresRDVSP, PlageRDVSP, RdvRDVSP, prefixe_references)

logger = logging.getLogger(__name__)

JOURS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
RENOUVELER_AVANT = 21          # jours : une publication qui expire bientôt est prolongée
STATUTS_VERS_CID = {           # RDV-Solidarités → CID
    "unknown": "RESERVE", "seen": "VENU_RECU", "noshow": "ABSENT",
    "excused": "ANNULE_USAGER", "revoked": "ANNULE_MDS",
}
STATUTS_VERS_SP = {"VENU_RECU": "seen", "ABSENT": "noshow", "VENU_NON_RECU": "seen", "ANNULE_MDS": "revoked",
                   "ANNULE_USAGER": "excused"}


class SynchroErreur(Exception):
    pass


# --- Activation et client -----------------------------------------------------
def secret_avis():
    return os.environ.get("RDVSP_SECRET_AVIS", "").strip()


def prete():
    """Passerelle activée ET compte de synchronisation relié."""
    p = ParametresRDVSP.get()
    return api.est_actif() and p.compte_synchro_id is not None and api.compte_relie(p.compte_synchro)


def client():
    p = ParametresRDVSP.get()
    if not api.est_actif():
        raise SynchroErreur("La passerelle RDV-Solidarités n'est pas activée.")
    if not p.compte_synchro_id:
        raise SynchroErreur("Aucun compte de synchronisation choisi.")
    return api.Client(p.compte_synchro)


def _tracer(action, reussi, code=None):
    try:
        AppelRDVSP.objects.create(utilisateur=ParametresRDVSP.get().compte_synchro, action=action,
                                  reussi=reussi, code_http=code)
    except Exception:
        logger.exception("rdvsp: traçabilité impossible")


def _corps(reponse, cle):
    """Les réponses arrivent soit enveloppées ({"lieu": {...}}), soit directement (vérifié sur le banc d'essai)."""
    return reponse.get(cle) if isinstance(reponse.get(cle), dict) else reponse


# --- 1. Publication -----------------------------------------------------------
def _adresse(mds):
    return " ".join(x for x in [(mds.adresse or "").replace("\n", " ").strip(), mds.code_postal, mds.ville] if x)


def publier_lieu_et_motifs(c, mds_sp):
    """Lieu de la MDS et motifs ouverts en ligne, créés une fois avec la référence CID."""
    p = ParametresRDVSP.get()
    if not mds_sp.lieu_sp_id:
        mds = mds_sp.mds
        corps = {"organisation_id": mds_sp.organisation_sp_id, "name": mds.nom, "address": _adresse(mds),
                 "availability": "enabled", "external_reference": {"external_id": mds_sp.reference_lieu}}
        if getattr(mds, "latitude", None) and getattr(mds, "longitude", None):
            corps.update(latitude=float(mds.latitude), longitude=float(mds.longitude))
        else:
            corps["address_without_geocoding"] = True
        try:
            lieu = _corps(c.appel("POST", "/lieux", json=corps), "lieu")
        except api.RDVSPErreur as e:
            # Déjà créé (base CID réinitialisée…) : on reprend le lieu existant de l'organisation, par son nom
            lieu = _deja_cree(e, c.get("/lieux").get("lieux", []), mds_sp, mds.nom)
        mds_sp.lieu_sp_id = lieu["id"]
        mds_sp.save(update_fields=["lieu_sp_id"])
    for motif in MotifRDVSP.objects.filter(actif=True):
        if MotifRDVSPPublie.objects.filter(motif=motif, mds_sp=mds_sp).exists():
            continue
        corps = {
            "organisation_id": mds_sp.organisation_sp_id, "name": motif.nom, "color": motif.couleur,
            "default_duration_in_min": motif.duree_minutes, "location_type": "public_office",
            "min_public_booking_delay": motif.delai_min_heures * 3600,
            "max_public_booking_delay": motif.delai_max_jours * 86400,
            "bookable_by": "agents_and_prescripteurs_and_invited_users" if motif.sur_invitation else "everyone",
            "external_reference": {"external_id": motif.reference(mds_sp)},
        }
        if p.service_sp_id:
            corps["service_id"] = p.service_sp_id
        try:
            m = _corps(c.appel("POST", "/motifs", json=corps), "motif")
        except api.RDVSPErreur as e:
            existants = c.get(f"/organisations/{mds_sp.organisation_sp_id}/motifs").get("motifs", [])
            m = _deja_cree(e, existants, mds_sp, motif.nom)
        MotifRDVSPPublie.objects.create(motif=motif, mds_sp=mds_sp, motif_sp_id=m["id"])


def _deja_cree(erreur, existants, mds_sp, nom):
    if "déjà utilisé" not in str(erreur) and "already" not in str(erreur):
        raise erreur
    for x in existants:
        if x.get("name") == nom and x.get("organisation_id") in (None, mds_sp.organisation_sp_id):
            return x
    raise SynchroErreur(f"{nom} : référence déjà utilisée dans RDV-Solidarités, mais introuvable dans "
                        f"l'organisation {mds_sp.organisation_sp_id} (préfixe RDVSP_PREFIXE à changer ?).")


def _prochain(jour, jour_semaine):
    return jour + timedelta(days=(jour_semaine - jour.weekday()) % 7)


def demi_journees_a_publier():
    from mds.models import DemiJourneeReception
    return (DemiJourneeReception.objects.filter(actif=True, type_lieu="MDS", mds__rdvsp__en_ligne=True)
            .exclude(agent__email="").select_related("agent", "mds", "mds__rdvsp"))


def _publier_plage(c, dj, debut, semaines):
    mds_sp = dj.mds.rdvsp
    premier = _prochain(debut, dj.jour_semaine)
    dernier = premier + timedelta(weeks=semaines - 1)
    motifs = [m.motif.reference(mds_sp) for m in mds_sp.motifs.select_related("motif").filter(motif__actif=True)]
    if not motifs:
        raise SynchroErreur(f"{dj.mds} : aucun motif en ligne publié.")
    recurrence = {"every": "week", "on": [JOURS[dj.jour_semaine]], "interval": 1,
                  "starts": premier.isoformat(), "until": dernier.isoformat()}
    reponse = c.appel("POST", "/plage_ouvertures", json={
        "organisation_id": mds_sp.organisation_sp_id, "agent_email": dj.agent.email,
        "title": f"Permanence {dj.get_type_demi_journee_display().lower()} (CID)",
        "first_day": premier.isoformat(), "start_time": dj.heure_debut.strftime("%H:%M"),
        "end_time": dj.heure_fin.strftime("%H:%M"), "lieu_external_id": mds_sp.reference_lieu,
        "motif_external_ids": motifs, "recurrence": json.dumps(recurrence),
        "external_reference": {"external_id": f"{prefixe_references()}-dj-{dj.pk}-{premier.isoformat()}"},
    })
    plage = _corps(reponse, "plage_ouverture")
    return PlageRDVSP.objects.create(
        demi_journee=dj, mds=dj.mds, agent=dj.agent, jour_semaine=dj.jour_semaine, heure_debut=dj.heure_debut,
        heure_fin=dj.heure_fin, premier_jour=premier, dernier_jour=dernier, plage_sp_id=plage["id"])


def _neutraliser(c, plage):
    """Une permanence publiée ne s'efface pas par l'API : on la couvre d'une absence répétée jusqu'à sa fin."""
    debut = max(plage.premier_jour, timezone.localdate())
    debut = _prochain(debut, plage.jour_semaine)
    if debut <= plage.dernier_jour:
        recurrence = {"every": "week", "on": [JOURS[plage.jour_semaine]], "interval": 1,
                      "starts": debut.isoformat(), "until": plage.dernier_jour.isoformat()}
        a = _corps(c.appel("POST", "/absences", json={
            "agent_email": plage.agent.email, "title": "Permanence retirée dans CID", "first_day": debut.isoformat(),
            "start_time": plage.heure_debut.strftime("%H:%M"), "end_time": plage.heure_fin.strftime("%H:%M"),
            "recurrence": json.dumps(recurrence)}), "absence")
        AbsenceRDVSP.objects.create(raison=AbsenceRDVSP.RETRAIT, agent=plage.agent, date=debut,
                                    heure_debut=plage.heure_debut, heure_fin=plage.heure_fin,
                                    absence_sp_id=a["id"], plage=plage)
    plage.neutralisee = True
    plage.save(update_fields=["neutralisee"])


def _identique(plage, dj):
    return (plage.agent_id == dj.agent_id and plage.jour_semaine == dj.jour_semaine
            and plage.heure_debut == dj.heure_debut and plage.heure_fin == dj.heure_fin and plage.mds_id == dj.mds_id)


def synchroniser(aujourd_hui=None):
    """Publie / prolonge / neutralise les permanences. Renvoie un compte rendu {clé: nombre, 'erreurs': [...]}."""
    aujourd_hui = aujourd_hui or timezone.localdate()
    c = client()
    p = ParametresRDVSP.get()
    bilan = {"publiees": 0, "prolongees": 0, "neutralisees": 0, "erreurs": []}
    for mds_sp in MdsRDVSP.objects.filter(en_ligne=True).select_related("mds"):
        try:
            publier_lieu_et_motifs(c, mds_sp)
        except api.RDVSPErreur as e:
            bilan["erreurs"].append(f"{mds_sp.mds} : {e}")
    # Permanences retirées ou modifiées dans CID
    a_publier = {dj.pk: dj for dj in demi_journees_a_publier()}
    for plage in PlageRDVSP.objects.filter(neutralisee=False, dernier_jour__gte=aujourd_hui).select_related("agent"):
        dj = a_publier.get(plage.demi_journee_id)
        if dj is None or not _identique(plage, dj):
            try:
                _neutraliser(c, plage)
                bilan["neutralisees"] += 1
            except api.RDVSPErreur as e:
                bilan["erreurs"].append(f"{plage} : {e}")
    # Publications nouvelles ou à prolonger
    for dj in a_publier.values():
        actives = PlageRDVSP.objects.filter(demi_journee=dj, neutralisee=False, dernier_jour__gte=aujourd_hui)
        derniere = actives.order_by("-dernier_jour").first()
        if derniere and (derniere.dernier_jour - aujourd_hui).days >= RENOUVELER_AVANT:
            continue
        debut = (derniere.dernier_jour + timedelta(days=1)) if derniere else aujourd_hui + timedelta(days=1)
        try:
            _publier_plage(c, dj, debut, p.semaines_publication)
            bilan["prolongees" if derniere else "publiees"] += 1
        except (api.RDVSPErreur, SynchroErreur) as e:
            bilan["erreurs"].append(f"{dj} : {e}")
    # Rattrapage des blocages (créneaux pris et jours bloqués dans la période publiée)
    bilan["blocages"] = rattraper_blocages(c, aujourd_hui)
    p.derniere_synchro = timezone.now()
    p.save(update_fields=["derniere_synchro"])
    _tracer("SYNCHRO", not bilan["erreurs"])
    return bilan


# --- 2. Blocages --------------------------------------------------------------
def _plage_de(agent_id, jour, debut, fin):
    for plage in PlageRDVSP.objects.filter(agent_id=agent_id, neutralisee=False, premier_jour__lte=jour,
                                           dernier_jour__gte=jour, jour_semaine=jour.weekday()):
        if plage.couvre(jour, debut, fin):
            return plage
    return None


def _creer_absence(c, raison, agent, jour, debut, fin, titre, **liens):
    a = _corps(c.appel("POST", "/absences", json={
        "agent_email": agent.email, "title": titre, "first_day": jour.isoformat(),
        "start_time": debut.strftime("%H:%M"), "end_time": fin.strftime("%H:%M")}), "absence")
    return AbsenceRDVSP.objects.create(raison=raison, agent=agent, date=jour, heure_debut=debut, heure_fin=fin,
                                       absence_sp_id=a["id"], **liens)


def _supprimer_absences(c, absences):
    for a in list(absences):
        try:
            c.appel("DELETE", f"/absences/{a.absence_sp_id}")
        except api.RDVSPErreur as e:
            if "(404)" not in str(e):
                raise
        a.delete()


def _creneau_bloquant(creneau):
    """Un créneau CID occupe le temps de l'agent (hors RDV venus de RDV-Solidarités, déjà connus là-bas)."""
    from planning.models import STATUTS_ANNULES
    if creneau.statut == "DISPONIBLE" or creneau.statut in STATUTS_ANNULES:
        return False
    return not RdvRDVSP.objects.filter(creneau=creneau).exists()


def maj_blocage_creneau(creneau, c=None, supprime=False):
    """Appelé à chaque enregistrement ou suppression d'un créneau CID (signaux)."""
    existantes = AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.CRENEAU, creneau=creneau) if creneau.pk else \
        AbsenceRDVSP.objects.none()
    bloque = (not supprime and creneau.agent_id and creneau.date >= timezone.localdate()
              and _creneau_bloquant(creneau)
              and _plage_de(creneau.agent_id, creneau.date, creneau.heure_debut, creneau.heure_fin) is not None)
    if bloque and not existantes.exists():
        c = c or client()
        _creer_absence(c, AbsenceRDVSP.CRENEAU, creneau.agent, creneau.date, creneau.heure_debut, creneau.heure_fin,
                       "Créneau pris dans CID", creneau=creneau)
    elif not bloque and existantes.exists():
        _supprimer_absences(c or client(), existantes)


def maj_blocage_jour(jour_bloque, c=None, supprime=False):
    """Jour bloqué CID (fermeture, férié, indisponibilité d'un agent) dans une période publiée."""
    existantes = AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.JOUR_BLOQUE, jour_bloque=jour_bloque)
    if supprime or jour_bloque.date < timezone.localdate():
        if existantes.exists():
            _supprimer_absences(c or client(), existantes)
        return
    plages = PlageRDVSP.objects.filter(neutralisee=False, premier_jour__lte=jour_bloque.date,
                                       dernier_jour__gte=jour_bloque.date, jour_semaine=jour_bloque.date.weekday())
    if jour_bloque.agent_id:
        plages = plages.filter(agent_id=jour_bloque.agent_id)
    elif jour_bloque.salle_id:
        plages = plages.filter(mds_id=jour_bloque.salle.mds_id)
    deja = set(existantes.values_list("agent_id", "heure_debut"))
    for plage in plages.select_related("agent"):
        debut, fin = max(plage.heure_debut, jour_bloque.heure_debut), min(plage.heure_fin, jour_bloque.heure_fin)
        if debut >= fin or (plage.agent_id, debut) in deja:
            continue
        c = c or client()
        _creer_absence(c, AbsenceRDVSP.JOUR_BLOQUE, plage.agent, jour_bloque.date, debut, fin,
                       "Fermeture (CID)", jour_bloque=jour_bloque, plage=plage)


def maj_plafond(agent_id, jour, c=None):
    """Plafond de RDV en ligne par demi-journée : au-delà, la demi-journée est fermée en ligne."""
    for plage in PlageRDVSP.objects.filter(agent_id=agent_id, neutralisee=False, premier_jour__lte=jour,
                                           dernier_jour__gte=jour, jour_semaine=jour.weekday()).select_related("agent"):
        plafond = min((m.plafond_demi_journee for m in MotifRDVSP.objects.filter(actif=True)), default=0)
        debut_dt = timezone.make_aware(datetime.combine(jour, plage.heure_debut))
        fin_dt = timezone.make_aware(datetime.combine(jour, plage.heure_fin))
        en_ligne = [r for r in RdvRDVSP.objects.filter(agent_id=agent_id, cree_par_usager=True,
                                                       debut__gte=debut_dt, debut__lt=fin_dt) if r.actif]
        existantes = AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.PLAFOND, agent_id=agent_id, date=jour,
                                                 plage=plage)
        atteint = plafond and len(en_ligne) >= plafond
        if atteint and not existantes.exists():
            c = c or client()
            _creer_absence(c, AbsenceRDVSP.PLAFOND, plage.agent, jour, plage.heure_debut, plage.heure_fin,
                           "Plafond de RDV en ligne atteint (CID)", plage=plage)
        elif not atteint and existantes.exists():
            _supprimer_absences(c or client(), existantes)


def rattraper_blocages(c, aujourd_hui):
    """Après une publication : bloque ce qui était déjà pris ou fermé dans CID sur la période publiée."""
    from planning.models import CreneauRdv, JourBloque
    n = 0
    fin = PlageRDVSP.objects.filter(neutralisee=False).order_by("-dernier_jour").values_list("dernier_jour", flat=True).first()
    if not fin:
        return 0
    agents = PlageRDVSP.objects.filter(neutralisee=False).values_list("agent_id", flat=True)
    for cr in (CreneauRdv.objects.filter(agent_id__in=agents, date__range=(aujourd_hui, fin))
               .exclude(statut="DISPONIBLE").select_related("agent")):
        if not AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.CRENEAU, creneau=cr).exists():
            maj_blocage_creneau(cr, c)
            n += AbsenceRDVSP.objects.filter(raison=AbsenceRDVSP.CRENEAU, creneau=cr).count()
    for jb in JourBloque.objects.filter(date__range=(aujourd_hui, fin)):
        avant = AbsenceRDVSP.objects.filter(jour_bloque=jb).count()
        maj_blocage_jour(jb, c)
        n += AbsenceRDVSP.objects.filter(jour_bloque=jb).count() - avant
    return n


# --- 3. Retour des RDV pris dans RDV-Solidarités --------------------------------
def signature_valide(corps_brut, signature):
    s = secret_avis()
    if not s or not signature:
        return False
    attendu = hmac.new(s.encode(), corps_brut, hashlib.sha256).hexdigest()
    return hmac.compare_digest(attendu, signature.strip())


def _date_sp(texte):
    """« 2026-11-16 09:30:00 +0100 » ou ISO 8601 → datetime avec fuseau."""
    if not texte:
        return None
    d = parse_datetime(texte)
    if d is None:
        try:
            d = datetime.strptime(texte, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            return None
    return d if timezone.is_aware(d) else timezone.make_aware(d)


def recevoir_avis(corps_brut):
    """Enregistre l'avis puis le traite. Renvoie l'AvisRDVSP (traite=True si tout s'est bien passé)."""
    try:
        d = json.loads(corps_brut)
    except ValueError:
        return AvisRDVSP.objects.create(erreur="Avis illisible (JSON invalide).")
    meta, data = d.get("meta") or {}, d.get("data") or {}
    avis = AvisRDVSP.objects.create(modele=str(meta.get("model", ""))[:40], evenement=str(meta.get("event", ""))[:20],
                                    objet_sp_id=data.get("id") if isinstance(data.get("id"), int) else None, corps=d)
    try:
        if avis.modele == "Rdv":
            traiter_rdv(data, avis.evenement)
        avis.traite = True
    except Exception as e:  # l'avis reste consultable pour reprise
        logger.exception("rdvsp: avis non traité")
        avis.erreur = f"{type(e).__name__} : {e}"[:500]
    avis.save(update_fields=["traite", "erreur"])
    return avis


def _agent_cid(data):
    User = get_user_model()
    for a in data.get("agents") or []:
        u = User.objects.filter(email__iexact=a.get("email", "")).exclude(email="").first()
        if u:
            return u
    return None


@transaction.atomic
def traiter_rdv(data, evenement):
    from planning.models import CreneauRdv, HistoriqueCreneau
    rdv_id = data["id"]
    lien = RdvRDVSP.objects.select_for_update().filter(rdv_sp_id=rdv_id).first()
    statut_sp = "revoked" if evenement == "destroyed" else (data.get("status") or "unknown")
    debut = _date_sp(data.get("starts_at")) or (lien.debut if lien else None)
    fin = _date_sp(data.get("ends_at")) or (debut + timedelta(minutes=data.get("duration_in_min") or 30))
    if debut is None:
        raise SynchroErreur("RDV sans date de début.")
    agent = _agent_cid(data) or (lien.agent if lien else None)
    usagers = data.get("users") or []
    usager_sp_id = usagers[0].get("id") if usagers else None
    beneficiaire = None
    if usager_sp_id:
        l = LienUsagerRDVSP.objects.filter(usager_rdvsp_id=str(usager_sp_id)).select_related("beneficiaire").first()
        beneficiaire = l.beneficiaire if l else None
    org = (data.get("organisation") or {}).get("id")
    mds_sp = MdsRDVSP.objects.filter(organisation_sp_id=org).select_related("mds").first() if org else None
    motif = (data.get("motif") or {}).get("name", "")
    annule_le = _date_sp(data.get("cancelled_at"))

    if lien is None:
        lien = RdvRDVSP(rdv_sp_id=rdv_id)
    lien.mds = mds_sp.mds if mds_sp else lien.mds
    lien.agent, lien.beneficiaire, lien.usager_sp_id = agent, beneficiaire or lien.beneficiaire, usager_sp_id
    lien.motif, lien.debut, lien.fin = motif[:150], debut, fin
    lien.cree_par_usager = data.get("created_by") == "user" or data.get("created_by_type") == "User"
    lien.statut_sp, lien.annule_le = statut_sp, annule_le if statut_sp in ("excused", "revoked") else None
    lien.a_rapprocher = agent is None or (usager_sp_id is not None and lien.beneficiaire is None)

    statut_cid = STATUTS_VERS_CID.get(statut_sp, "RESERVE")
    jour, h_debut, h_fin = timezone.localtime(debut).date(), timezone.localtime(debut).time(), timezone.localtime(fin).time()
    creneau = lien.creneau
    if creneau is None and agent and statut_cid == "RESERVE":
        creneau = (CreneauRdv.objects.select_for_update()
                   .filter(agent=agent, date=jour, heure_debut=h_debut, statut="DISPONIBLE").first())
        if creneau is None:
            creneau = CreneauRdv(agent=agent, date=jour, heure_debut=h_debut, heure_fin=h_fin,
                                 duree_minutes=int((fin - debut).total_seconds() // 60) or 30,
                                 mds=lien.mds, statut="DISPONIBLE")
    if creneau is not None:
        ancien = creneau.statut
        creneau._depuis_rdvsp = True
        creneau.statut = statut_cid
        creneau.date, creneau.heure_debut, creneau.heure_fin = jour, h_debut, h_fin
        creneau.beneficiaire = lien.beneficiaire or creneau.beneficiaire
        creneau.nature, creneau.domaine = "PERMANENCE", "INSERTION"
        creneau.mds = creneau.mds or lien.mds
        creneau.description = f"{motif} — réservé en ligne (RDV-Solidarités)" if lien.cree_par_usager else \
            f"{motif} — RDV-Solidarités"
        if statut_cid == "RESERVE" and not creneau.date_reservation:
            creneau.date_reservation = timezone.now()
        creneau.save()
        if ancien != creneau.statut:
            HistoriqueCreneau.objects.create(creneau=creneau, action="MODIFICATION", utilisateur=None,
                                             commentaire=f"RDV-Solidarités : {ancien} → {creneau.statut}")
        # Annulé en ligne : le temps de l'agent redevient libre dans CID aussi
        if ancien == "RESERVE" and statut_sp in ("excused", "revoked") and jour >= timezone.localdate():
            if not CreneauRdv.objects.filter(agent=agent, date=jour, heure_debut=h_debut,
                                             statut="DISPONIBLE").exists():
                libre = CreneauRdv(agent=agent, date=jour, heure_debut=h_debut, heure_fin=h_fin,
                                   duree_minutes=creneau.duree_minutes, salle=creneau.salle, mds=creneau.mds,
                                   statut="DISPONIBLE", description="Créneau libéré (annulation en ligne)")
                libre._depuis_rdvsp = True
                libre.save()
    lien.creneau = creneau
    lien.save()
    if agent:
        transaction.on_commit(lambda: _plafond_sans_erreur(agent.pk, jour))
    return lien


def _plafond_sans_erreur(agent_id, jour):
    try:
        maj_plafond(agent_id, jour)
    except Exception:
        logger.exception("rdvsp: plafond non mis à jour")


# --- 4. Statuts CID → RDV-Solidarités ---------------------------------------------
def renvoyer_statut(creneau):
    lien = RdvRDVSP.objects.filter(creneau=creneau).first()
    statut = STATUTS_VERS_SP.get(creneau.statut)
    if not lien or not statut or lien.statut_sp == statut:
        return
    client().appel("PATCH", f"/rdvs/{lien.rdv_sp_id}/update_status", json={"status": statut})
    RdvRDVSP.objects.filter(pk=lien.pk).update(statut_sp=statut)


# --- Déclaration de l'adresse de CID ---------------------------------------------
def declarer_avis(url_avis):
    """Déclare l'adresse des avis automatiques pour chaque organisation (administrateur de l'espace requis)."""
    if not secret_avis():
        raise SynchroErreur("RDVSP_SECRET_AVIS n'est pas renseigné.")
    c = client()
    res = []
    for mds_sp in MdsRDVSP.objects.filter(en_ligne=True, avis_declare=False).select_related("mds"):
        try:
            c.appel("POST", f"/organisations/{mds_sp.organisation_sp_id}/webhook_endpoints", json={
                "target_url": url_avis, "secret": secret_avis(), "subscriptions": ["rdv"]})
            mds_sp.avis_declare = True
            mds_sp.save(update_fields=["avis_declare"])
            res.append((mds_sp.mds, None))
        except api.RDVSPErreur as e:
            res.append((mds_sp.mds, str(e)))
    return res


def purger_avis(jours=30):
    """Les avis contiennent des données personnelles : leur contenu est effacé après 30 jours."""
    limite = timezone.now() - timedelta(days=jours)
    return AvisRDVSP.objects.filter(recu_le__lt=limite).exclude(corps={}).update(corps={})
