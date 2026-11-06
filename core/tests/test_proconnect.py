# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/tests/test_proconnect.py
"""ProConnect : désactivé sans identifiants ; parcours complet contre un faux ProConnect (clé RSA de test tirée au
hasard) ; state, nonce et signature vérifiés ; pas de création de compte ; lien par sub ; déconnexion. Fictif."""
import json
import os
import time
from unittest import mock
from urllib.parse import parse_qs, urlparse

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import Client, TestCase

from core import proconnect as pc
from core.models import IdentiteProConnect, User

CLE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
JWK = {**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(CLE.public_key())), "kid": "k1", "alg": "RS256", "use": "sig"}
D = "proconnect.exemple.test"
ENV = {"PROCONNECT_DOMAIN": D, "PROCONNECT_CLIENT_ID": "cid-test", "PROCONNECT_CLIENT_SECRET": "secret-test",
       "PROCONNECT_ALGORITHME": "RS256", "PROCONNECT_IDP_HINT": ""}
DECOUVERTE = {"issuer": f"https://{D}/api/v2", "authorization_endpoint": f"https://{D}/api/v2/authorize",
              "token_endpoint": f"https://{D}/api/v2/token", "userinfo_endpoint": f"https://{D}/api/v2/userinfo",
              "end_session_endpoint": f"https://{D}/api/v2/session/end", "jwks_uri": f"https://{D}/api/v2/jwks"}


def signer(donnees, cle=CLE):
    return jwt.encode({"iss": DECOUVERTE["issuer"], "aud": "cid-test", "exp": int(time.time()) + 60, **donnees},
                      cle, algorithm="RS256", headers={"kid": "k1"})


class FauxProConnect:
    def __init__(self, email="agent.fictif@exemple.gouv.fr", sub="sub-1", nonce_faux=False, cle=CLE):
        self.email, self.sub, self.nonce_faux, self.cle = email, sub, nonce_faux, cle
        self.nonce = None

    def get(self, url, headers=None, timeout=None, **kw):
        r = mock.Mock(status_code=200, headers={})
        if url.endswith("openid-configuration"):
            r.json.return_value = DECOUVERTE
        elif url == DECOUVERTE["jwks_uri"]:
            r.json.return_value = {"keys": [JWK]}
        elif url == DECOUVERTE["userinfo_endpoint"]:
            r.headers = {"Content-Type": "application/jwt"}
            r.text = signer({"sub": self.sub, "email": self.email, "given_name": "Camille", "usual_name": "FICTIF",
                             "siret": "00000000000001", "idp_id": "fi-1"}, self.cle)
        return r

    def post(self, url, data=None, timeout=None, **kw):
        r = mock.Mock(status_code=200)
        r.json.return_value = {"access_token": "at", "id_token": signer(
            {"sub": self.sub, "nonce": "autre" if self.nonce_faux else self.nonce, "idp_id": "fi-1"}, self.cle)}
        return r


class ProConnectTests(TestCase):
    def setUp(self):
        pc._cache.clear()
        self.compte = User.objects.create_user("camille", password="x", matricule="CAM",
                                               email="Agent.Fictif@exemple.gouv.fr")

    def parcours(self, faux, client=None, falsifier_state=False):
        c = client or Client(HTTP_HOST="localhost")
        with mock.patch.dict(os.environ, ENV), mock.patch("core.proconnect.requests.get", side_effect=faux.get), \
                mock.patch("core.proconnect.requests.post", side_effect=faux.post):
            r = c.get("/connexion/proconnect/")
            q = parse_qs(urlparse(r["Location"]).query)
            self.assertEqual((q["client_id"][0], q["acr_values"][0]), ("cid-test", "eidas1"))
            self.assertIn("siret", q["scope"][0])
            faux.nonce = q["nonce"][0]
            state = "x" * 40 if falsifier_state else q["state"][0]
            return c, c.get(f"/connexion/proconnect/retour/?code=abc&state={state}", follow=True)

    def test_desactive_sans_identifiants(self):
        with mock.patch.dict(os.environ, {k: "" for k in ENV}):
            c = Client(HTTP_HOST="localhost")
            self.assertNotContains(c.get("/login/"), "ProConnect</b>")
            self.assertEqual(c.get("/connexion/proconnect/").status_code, 404)
        with mock.patch.dict(os.environ, ENV):
            self.assertContains(Client(HTTP_HOST="localhost").get("/login/"), "ProConnect</b>")

    def test_connexion_et_lien(self):
        c, r = self.parcours(FauxProConnect())
        self.assertEqual(int(c.session["_auth_user_id"]), self.compte.pk)
        lien = IdentiteProConnect.objects.get()
        self.assertEqual((lien.sub, lien.idp_id, lien.siret), ("sub-1", "fi-1", "00000000000001"))
        # la fois suivante, le lien par sub suffit même si le courriel a changé
        _, r = self.parcours(FauxProConnect(email="nouveau@exemple.gouv.fr"))
        self.assertEqual(IdentiteProConnect.objects.count(), 1)

    def test_pas_de_creation_de_compte(self):
        c, r = self.parcours(FauxProConnect(email="inconnu@exemple.gouv.fr", sub="sub-9"))
        self.assertNotIn("_auth_user_id", c.session)
        self.assertContains(r, "Aucun compte CID actif")
        self.assertEqual(User.objects.count(), 1)

    def test_compte_desactive_refuse(self):
        self.compte.is_active = False
        self.compte.save()
        c, r = self.parcours(FauxProConnect())
        self.assertNotIn("_auth_user_id", c.session)

    def test_state_nonce_signature(self):
        c, r = self.parcours(FauxProConnect(), falsifier_state=True)
        self.assertContains(r, "state")
        self.assertNotIn("_auth_user_id", c.session)
        c, r = self.parcours(FauxProConnect(nonce_faux=True))
        self.assertContains(r, "Nonce invalide")
        pirate = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        c, r = self.parcours(FauxProConnect(cle=pirate))
        self.assertContains(r, "Jeton refusé")
        self.assertNotIn("_auth_user_id", c.session)

    def test_deconnexion_ferme_proconnect(self):
        faux = FauxProConnect()
        c, _ = self.parcours(faux)
        with mock.patch.dict(os.environ, ENV), mock.patch("core.proconnect.requests.get", side_effect=faux.get):
            r = c.post("/logout/")
        self.assertTrue(r["Location"].startswith(DECOUVERTE["end_session_endpoint"]))
        self.assertIn("id_token_hint", r["Location"])
        self.assertNotIn("_auth_user_id", c.session)
        # déconnexion classique inchangée
        c2 = Client(HTTP_HOST="localhost")
        c2.force_login(self.compte)
        self.assertEqual(c2.post("/logout/")["Location"], "/")          # comme avant (LOGOUT_REDIRECT_URL)
