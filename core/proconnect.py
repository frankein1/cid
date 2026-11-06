# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/proconnect.py
"""
Connexion par ProConnect (DINUM, OpenID Connect « authorization code flow »). PRÊT MAIS DÉSACTIVÉ : rien ne s'affiche
tant que la DSI n'a pas fourni les identifiants (variables d'environnement) :

    PROCONNECT_DOMAIN         ex. fca.integ01.dev-agentconnect.fr (intégration), domaine de production fourni par la DINUM
    PROCONNECT_CLIENT_ID      fournis par l'équipe ProConnect (Démarches simplifiées)
    PROCONNECT_CLIENT_SECRET
    PROCONNECT_ALGORITHME     algorithme de signature choisi à l'inscription : RS256 (défaut), ES256 ou HS256
    PROCONNECT_IDP_HINT       facultatif : envoyer directement vers le fournisseur d'identité du Département

Règles :
- **pas de création automatique de compte** : un compte CID donne accès à des données sociales ; la personne doit
  avoir un compte actif créé par un administrateur, retrouvé par son courriel professionnel à la première connexion,
  puis par l'identifiant ProConnect (sub + fournisseur d'identité) ;
- state et nonce aléatoires vérifiés, jetons signés vérifiés (clés publiques de ProConnect, ou secret en HS256) ;
- à la déconnexion de CID, la session ProConnect est fermée aussi.
"""
import os
import secrets
import time

import jwt
import requests

SCOPES = "openid given_name usual_name email uid siret idp_id"
_cache = {}


class ErreurProConnect(Exception):
    pass


def config():
    return {"domaine": os.environ.get("PROCONNECT_DOMAIN", "").strip().rstrip("/"),
            "client_id": os.environ.get("PROCONNECT_CLIENT_ID", "").strip(),
            "secret": os.environ.get("PROCONNECT_CLIENT_SECRET", "").strip(),
            "algorithme": os.environ.get("PROCONNECT_ALGORITHME", "RS256").strip() or "RS256",
            "idp_hint": os.environ.get("PROCONNECT_IDP_HINT", "").strip()}


def actif():
    c = config()
    return bool(c["domaine"] and c["client_id"] and c["secret"])


def decouverte():
    c = config()
    cle = c["domaine"]
    if cle in _cache and _cache[cle][0] > time.time():
        return _cache[cle][1]
    r = requests.get(f"https://{c['domaine']}/api/v2/.well-known/openid-configuration", timeout=10)
    r.raise_for_status()
    _cache[cle] = (time.time() + 3600, r.json())
    return _cache[cle][1]


def url_autorisation(request, redirect_uri):
    c, d = config(), decouverte()
    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    request.session["proconnect_state"], request.session["proconnect_nonce"] = state, nonce
    params = {"response_type": "code", "client_id": c["client_id"], "redirect_uri": redirect_uri, "scope": SCOPES,
              "state": state, "nonce": nonce, "acr_values": "eidas1"}
    if c["idp_hint"]:
        params["idp_hint"] = c["idp_hint"]
    return requests.Request("GET", d["authorization_endpoint"], params=params).prepare().url


def _verifier(jeton, nonce=None):
    c, d = config(), decouverte()
    alg = c["algorithme"]
    if alg == "HS256":
        cle = c["secret"]
    else:
        entete = jwt.get_unverified_header(jeton)
        cles = requests.get(d["jwks_uri"], timeout=10).json().get("keys", [])
        jwk = next((k for k in cles if k.get("kid") == entete.get("kid")), None)
        if not jwk:
            raise ErreurProConnect("Clé de signature inconnue.")
        cle = jwt.PyJWK(jwk).key
    try:
        donnees = jwt.decode(jeton, cle, algorithms=[alg], audience=c["client_id"], issuer=d.get("issuer"),
                             options={"require": ["exp"] if nonce else []})
    except jwt.PyJWTError as e:
        raise ErreurProConnect(f"Jeton refusé : {e}") from e
    if nonce is not None and donnees.get("nonce") != nonce:
        raise ErreurProConnect("Nonce invalide (rejeu ?).")
    return donnees


def retour(request, redirect_uri):
    """Traite le retour de ProConnect ; renvoie (identite, id_token)."""
    state = request.session.pop("proconnect_state", None)
    nonce = request.session.pop("proconnect_nonce", None)
    if not state or request.GET.get("state") != state:
        raise ErreurProConnect("Réponse inattendue (state).")
    if request.GET.get("error"):
        raise ErreurProConnect(request.GET.get("error_description") or request.GET["error"])
    c, d = config(), decouverte()
    r = requests.post(d["token_endpoint"], data={
        "grant_type": "authorization_code", "code": request.GET.get("code", ""), "redirect_uri": redirect_uri,
        "client_id": c["client_id"], "client_secret": c["secret"]}, timeout=10)
    if r.status_code != 200:
        raise ErreurProConnect(f"Échange du code refusé ({r.status_code}).")
    jetons = r.json()
    id_token = jetons["id_token"]
    ident = _verifier(id_token, nonce)
    u = requests.get(d["userinfo_endpoint"], headers={"Authorization": f"Bearer {jetons['access_token']}"}, timeout=10)
    if u.status_code != 200:
        raise ErreurProConnect(f"Informations de l'agent indisponibles ({u.status_code}).")
    infos = _verifier(u.text) if "jwt" in u.headers.get("Content-Type", "") else u.json()
    if infos.get("sub") != ident.get("sub"):
        raise ErreurProConnect("Identité incohérente.")
    return {**infos, "idp_id": infos.get("idp_id") or ident.get("idp_id", "")}, id_token


def trouver_compte(identite):
    """Compte CID de la personne : par l'identifiant ProConnect déjà vu, sinon par courriel (compte créé à l'avance)."""
    from core.models import User
    from core.models import IdentiteProConnect
    lien = (IdentiteProConnect.objects.select_related("user")
            .filter(sub=identite["sub"], idp_id=identite.get("idp_id", "")).first())
    if lien:
        return lien.user if lien.user.is_active else None
    courriel = (identite.get("email") or "").strip()
    comptes = list(User.objects.filter(email__iexact=courriel, is_active=True)) if courriel else []
    if len(comptes) != 1:
        return None      # aucun compte, ou plusieurs comptes pour le même courriel : un administrateur doit trancher
    IdentiteProConnect.objects.create(user=comptes[0], sub=identite["sub"], idp_id=identite.get("idp_id", ""),
                                      siret=(identite.get("siret") or "")[:14], courriel=courriel[:254])
    return comptes[0]


def url_deconnexion(id_token, retour_url):
    d = decouverte()
    if not d.get("end_session_endpoint"):
        return None
    return requests.Request("GET", d["end_session_endpoint"], params={
        "id_token_hint": id_token, "state": secrets.token_urlsafe(32), "post_logout_redirect_uri": retour_url}).prepare().url
