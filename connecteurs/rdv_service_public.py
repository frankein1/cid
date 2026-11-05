# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/rdv_service_public.py
"""
Passerelle vers RDV Service Public (ANCT) — PRÉSENTE MAIS DÉSACTIVÉE PAR DÉFAUT.

Ce que fait la passerelle une fois activée :
  1. chaque agent relie son compte CID à son compte RDV Service Public (OAuth2, une fois) ;
  2. depuis la fiche usager, « Prendre RDV dans RDV Service Public » crée (ou met à jour)
     l'usager côté RDV-SP et ouvre directement l'écran de prise de rendez-vous ;
  3. CID peut relire les rendez-vous de l'usager et en mettre à jour le statut (venu, absent…).

Fonctionnement repris de Mon Suivi Social v2 (licence MIT), adapté à CID.

Variables d'environnement (rien n'est appelé tant qu'elles ne sont pas toutes renseignées) :
  RDVSP_ACTIF          « 1 » pour activer la passerelle (défaut : désactivée)
  RDVSP_URL            adresse de RDV Service Public (démonstration ou production, fournie par l'ANCT)
  RDVSP_CLIENT_ID      identifiant OAuth de CID, délivré par l'ANCT
  RDVSP_CLIENT_SECRET  secret OAuth associé
  RDVSP_REDIRECT_URI   (facultatif) adresse de retour déclarée à l'ANCT ;
                       par défaut : https://<serveur CID>/connecteurs/rdv-service-public/retour/
"""
import logging
import os
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.utils import timezone

from .models import AppelRDVSP, CompteRDVSP, LienUsagerRDVSP

logger = logging.getLogger(__name__)

DELAI = 15                # secondes
PORTEE = "write"
STATUTS_RDV = {           # statuts acceptés par RDV-SP → libellé CID
    "seen": "Venu",
    "noshow": "Absent",
    "excused": "Excusé",
    "revoked": "Annulé",
    "unknown": "À renseigner",
}


class RDVSPErreur(Exception):
    """Erreur lisible par l'agent (passerelle inactive, compte non relié, service indisponible…)."""


class ConnexionRequise(RDVSPErreur):
    """L'agent doit (re)relier son compte RDV Service Public."""


# --- Configuration -----------------------------------------------------------
def configuration():
    return {
        "actif": os.environ.get("RDVSP_ACTIF", "").strip() in ("1", "true", "oui"),
        "url": os.environ.get("RDVSP_URL", "").strip().rstrip("/"),
        "client_id": os.environ.get("RDVSP_CLIENT_ID", "").strip(),
        "client_secret": os.environ.get("RDVSP_CLIENT_SECRET", "").strip(),
        "redirect_uri": os.environ.get("RDVSP_REDIRECT_URI", "").strip(),
    }


def manques(conf=None):
    """Liste de ce qui manque pour activer la passerelle (vide = prête)."""
    conf = conf or configuration()
    noms = [("url", "RDVSP_URL"), ("client_id", "RDVSP_CLIENT_ID"), ("client_secret", "RDVSP_CLIENT_SECRET")]
    m = [var for cle, var in noms if not conf[cle]]
    if not conf["actif"]:
        m.append("RDVSP_ACTIF=1")
    return m


def est_actif():
    return not manques()


def _exiger_actif():
    conf = configuration()
    if manques(conf):
        raise RDVSPErreur("La passerelle RDV Service Public n'est pas activée.")
    return conf


def _tracer(user, action, code=None, reussi=False, beneficiaire=None):
    try:
        AppelRDVSP.objects.create(utilisateur=user, beneficiaire=beneficiaire, action=action,
                                  code_http=code, reussi=reussi)
    except Exception:  # la traçabilité ne doit jamais bloquer l'agent
        logger.exception("rdvsp: traçabilité impossible")


# --- OAuth2 (code d'autorisation) --------------------------------------------
def url_autorisation(redirect_uri, etat):
    conf = _exiger_actif()
    params = {"client_id": conf["client_id"], "redirect_uri": conf["redirect_uri"] or redirect_uri,
              "response_type": "code", "scope": PORTEE, "state": etat}
    return f"{conf['url']}/oauth/authorize?{urlencode(params)}"


def _jeton(donnees):
    conf = _exiger_actif()
    donnees = {**donnees, "client_id": conf["client_id"], "client_secret": conf["client_secret"]}
    try:
        r = requests.post(f"{conf['url']}/oauth/token", data=donnees, timeout=DELAI)
    except requests.RequestException as e:
        raise RDVSPErreur("RDV Service Public ne répond pas.") from e
    if r.status_code != 200:
        raise ConnexionRequise(f"Connexion refusée par RDV Service Public ({r.status_code}).")
    return r.json()


def _enregistrer(user, t, agent_id=None):
    compte, _ = CompteRDVSP.objects.update_or_create(utilisateur=user, defaults={
        "jeton_acces": t["access_token"],
        "jeton_renouvellement": t.get("refresh_token", ""),
        "expire_le": timezone.now() + timedelta(seconds=int(t.get("expires_in", 7200))),
    })
    if agent_id is not None:
        compte.agent_id = str(agent_id)
        compte.save(update_fields=["agent_id"])
    return compte


def finaliser_connexion(user, code, redirect_uri):
    """Échange le code reçu au retour d'autorisation contre un jeton, et identifie l'agent."""
    conf = _exiger_actif()
    t = _jeton({"grant_type": "authorization_code", "code": code,
                "redirect_uri": conf["redirect_uri"] or redirect_uri})
    compte = _enregistrer(user, t)
    try:
        moi = Client(user).get("/agents/me")
        compte.agent_id = str((moi.get("agent") or moi).get("id", ""))
        compte.save(update_fields=["agent_id"])
        _tracer(user, "CONNEXION", 200, True)
    except RDVSPErreur:
        _tracer(user, "CONNEXION", None, False)
        raise
    return compte


def compte_relie(user):
    return CompteRDVSP.objects.filter(utilisateur=user).exists()


# --- Appels à l'API, au nom de l'agent ---------------------------------------
class Client:
    def __init__(self, user):
        self.conf = _exiger_actif()
        self.user = user
        self.compte = CompteRDVSP.objects.filter(utilisateur=user).first()
        if not self.compte:
            raise ConnexionRequise("Reliez d'abord votre compte RDV Service Public.")

    def _jeton_valide(self):
        if self.compte.expire_le - timedelta(minutes=2) > timezone.now():
            return self.compte.jeton_acces
        if not self.compte.jeton_renouvellement:
            raise ConnexionRequise("Votre connexion RDV Service Public a expiré.")
        t = _jeton({"grant_type": "refresh_token", "refresh_token": self.compte.jeton_renouvellement})
        self.compte = _enregistrer(self.user, t)
        return self.compte.jeton_acces

    def appel(self, methode, chemin, **kw):
        entetes = {"Authorization": f"Bearer {self._jeton_valide()}", "Accept": "application/json"}
        try:
            r = requests.request(methode, f"{self.conf['url']}/api/v1{chemin}", headers=entetes,
                                 timeout=DELAI, **kw)
        except requests.RequestException as e:
            raise RDVSPErreur("RDV Service Public ne répond pas.") from e
        if r.status_code == 401:
            raise ConnexionRequise("Votre connexion RDV Service Public n'est plus valable.")
        if r.status_code >= 400:
            raise RDVSPErreur(f"RDV Service Public a refusé la demande ({r.status_code}).")
        self.dernier_code = r.status_code
        return r.json() if r.content else {}

    def get(self, chemin, **kw):
        return self.appel("GET", chemin, **kw)


def _usager(b, usager_id=None):
    """Données transmises : le strict nécessaire à la prise de rendez-vous."""
    u = {"first_name": b.prenom or "Non renseigné", "last_name": b.nom or "Non renseigné"}
    if usager_id:
        u["id"] = usager_id
    if b.email:
        u["email"] = b.email
    if b.telephone_mobile or b.telephone_fixe:
        u["phone_number"] = b.telephone_mobile or b.telephone_fixe
    adresse = " ".join(x for x in [(b.adresse or "").replace("\n", " ").strip(), b.code_postal, b.ville] if x)
    if adresse:
        u["address"] = adresse
    if b.date_naissance:
        u["birth_date"] = b.date_naissance.isoformat()
    return u


def preparer_rdv(user, beneficiaire, url_retour, url_dossier):
    """
    Crée un « plan de RDV » : renvoie l'adresse RDV-SP où l'agent choisit le motif et le créneau.
    L'identifiant usager RDV-SP est mémorisé pour les fois suivantes.
    """
    client = Client(user)
    lien = LienUsagerRDVSP.objects.filter(beneficiaire=beneficiaire).first()
    usager_id = lien.usager_rdvsp_id if lien else None
    try:
        if usager_id:  # coordonnées à jour côté RDV-SP (sans bloquer si ça échoue)
            try:
                client.appel("PATCH", f"/users/{usager_id}", json=_usager(beneficiaire))
            except ConnexionRequise:
                raise
            except RDVSPErreur:
                logger.warning("rdvsp: mise à jour de l'usager impossible")
        rep = client.appel("POST", "/rdv_plans", json={
            "user": _usager(beneficiaire, usager_id), "return_url": url_retour, "dossier_url": url_dossier})
        plan = rep["rdv_plan"]
    except (KeyError, TypeError) as e:
        _tracer(user, "PLAN_RDV", None, False, beneficiaire)
        raise RDVSPErreur("Réponse inattendue de RDV Service Public.") from e
    except RDVSPErreur:
        _tracer(user, "PLAN_RDV", None, False, beneficiaire)
        raise
    if not lien and plan.get("user_id"):
        LienUsagerRDVSP.objects.create(beneficiaire=beneficiaire, usager_rdvsp_id=str(plan["user_id"]))
    _tracer(user, "PLAN_RDV", client.dernier_code, True, beneficiaire)
    return plan["url"]


def rdvs_usager(user, beneficiaire):
    """Rendez-vous de l'usager côté RDV-SP (liste vide s'il n'y a jamais été inscrit)."""
    lien = LienUsagerRDVSP.objects.filter(beneficiaire=beneficiaire).first()
    if not lien:
        return []
    client = Client(user)
    try:
        rep = client.get("/rdvs", params={"user_id[]": [lien.usager_rdvsp_id],
                                          "include[]": ["motif", "users", "agents"]})
    except RDVSPErreur:
        _tracer(user, "LISTE_RDV", None, False, beneficiaire)
        raise
    _tracer(user, "LISTE_RDV", client.dernier_code, True, beneficiaire)
    return rep.get("rdvs", [])


def changer_statut(user, rdv_id, statut, beneficiaire=None):
    if statut not in STATUTS_RDV:
        raise RDVSPErreur("Statut de rendez-vous inconnu.")
    client = Client(user)
    try:
        rep = client.appel("PATCH", f"/rdvs/{int(rdv_id)}/update_status", json={"status": statut})
    except RDVSPErreur:
        _tracer(user, "STATUT_RDV", None, False, beneficiaire)
        raise
    _tracer(user, "STATUT_RDV", client.dernier_code, True, beneficiaire)
    return rep.get("rdv", rep)
