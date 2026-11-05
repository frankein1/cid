# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ged/chiffrement.py
"""
Chiffrement des fichiers de la GED (« chiffrement d'enveloppe », conception reprise de Mon Suivi Social v2).

- Chaque fichier est chiffré en AES-256-GCM avec SA PROPRE clé (clé de données, tirée au hasard).
- Cette clé de données est elle-même chiffrée par une CLÉ MAÎTRESSE, qui ne quitte jamais le gestionnaire
  de clés : seule la clé de données chiffrée est rangée, dans l'en-tête du fichier.
- Le stockage (pCloud, SeaweedFS…) ne voit donc que des fichiers illisibles ; la base ne contient aucune clé.
- L'en-tête est authentifié (données associées AES-GCM) : un fichier ou un en-tête modifié est refusé.

Format d'un fichier chiffré : MAGIQUE (8 octets) | longueur de l'en-tête (4 octets) | en-tête JSON
                              | nonce (12 octets) | contenu chiffré + étiquette (16 octets)
Un fichier sans MAGIQUE est un ancien fichier en clair : il reste lisible (voir la commande chiffrer_ged).

Gestionnaires de clés (variable GED_KMS) :
- « local » (défaut) : clé maîtresse dans la variable d'environnement GED_CLE_MAITRESSE (32 octets en base64),
  identifiée par GED_CLE_ID (défaut « k1 »). Anciennes clés pour la rotation : GED_CLES_ANCIENNES="k0:base64,…".
- « openbao » : moteur « transit » d'OpenBao ou de Vault (OPENBAO_ADDR, OPENBAO_TOKEN, OPENBAO_CLE ;
  OPENBAO_MOUNT, défaut « transit »). La clé maîtresse reste dans OpenBao.
Sans clé configurée, rien n'est chiffré (comportement d'avant) et la page d'état le signale.

⚠️ Perdre la clé maîtresse, c'est perdre TOUS les fichiers chiffrés : la sauvegarder hors de CID.
"""
import base64
import json
import logging
import os
import struct

import requests
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

MAGIQUE = b"CIDGED1\x00"
VERSION = 1
ALGO = "AES-256-GCM"


class ErreurChiffrement(Exception):
    """Fichier illisible : clé absente ou inconnue, fichier altéré…"""


def _b64(octets):
    return base64.b64encode(octets).decode()


def _deb64(texte):
    return base64.b64decode(texte)


# ------------------------------------------------------------------ gestionnaires de clés
class GestionnaireLocal:
    """Clé maîtresse dans les variables d'environnement. Simple ; pour la production, préférer OpenBao."""
    nom = "local"

    def __init__(self):
        self.cles = {}
        principale = os.environ.get("GED_CLE_MAITRESSE", "").strip()
        self.cle_id = os.environ.get("GED_CLE_ID", "k1").strip() or "k1"
        if principale:
            self.cles[self.cle_id] = self._lire(principale, "GED_CLE_MAITRESSE")
        for morceau in os.environ.get("GED_CLES_ANCIENNES", "").split(","):
            if ":" in morceau:
                kid, cle = morceau.split(":", 1)
                self.cles[kid.strip()] = self._lire(cle.strip(), f"GED_CLES_ANCIENNES ({kid.strip()})")

    @staticmethod
    def _lire(texte, origine):
        try:
            cle = _deb64(texte)
        except ValueError as e:
            raise ErreurChiffrement(f"{origine} n'est pas du base64 valide.") from e
        if len(cle) != 32:
            raise ErreurChiffrement(f"{origine} doit faire 32 octets (256 bits), pas {len(cle)}.")
        return cle

    @property
    def actif(self):
        return self.cle_id in self.cles

    def nouvelle_cle(self):
        """(clé de données en clair, clé de données chiffrée, identifiant de la clé maîtresse)"""
        cle = AESGCM.generate_key(bit_length=256)
        nonce = os.urandom(12)
        enveloppe = nonce + AESGCM(self.cles[self.cle_id]).encrypt(nonce, cle, self.cle_id.encode())
        return cle, _b64(enveloppe), self.cle_id

    def ouvrir_cle(self, cle_chiffree, cle_id):
        if cle_id not in self.cles:
            raise ErreurChiffrement(f"Clé maîtresse « {cle_id} » inconnue : fichier illisible.")
        brut = _deb64(cle_chiffree)
        try:
            return AESGCM(self.cles[cle_id]).decrypt(brut[:12], brut[12:], cle_id.encode())
        except InvalidTag as e:
            raise ErreurChiffrement("Clé de données altérée ou mauvaise clé maîtresse.") from e


class GestionnaireOpenBao:
    """Moteur transit d'OpenBao / Vault : la clé maîtresse ne sort jamais du gestionnaire."""
    nom = "openbao"

    def __init__(self):
        self.adresse = os.environ.get("OPENBAO_ADDR", "").rstrip("/")
        self.jeton = os.environ.get("OPENBAO_TOKEN", "")
        self.cle_id = os.environ.get("OPENBAO_CLE", "cid-ged")
        self.montage = os.environ.get("OPENBAO_MOUNT", "transit").strip("/")

    @property
    def actif(self):
        return bool(self.adresse and self.jeton)

    def _appel(self, chemin, corps):
        try:
            r = requests.post(f"{self.adresse}/v1/{self.montage}/{chemin}", json=corps, timeout=10,
                              headers={"X-Vault-Token": self.jeton})
        except requests.RequestException as e:
            raise ErreurChiffrement("Gestionnaire de clés injoignable.") from e
        if r.status_code != 200:
            raise ErreurChiffrement(f"Gestionnaire de clés : refus ({r.status_code}).")
        return r.json()["data"]

    def nouvelle_cle(self):
        d = self._appel(f"datakey/plaintext/{self.cle_id}", {"bits": 256})
        return _deb64(d["plaintext"]), d["ciphertext"], self.cle_id

    def ouvrir_cle(self, cle_chiffree, cle_id):
        return _deb64(self._appel(f"decrypt/{cle_id}", {"ciphertext": cle_chiffree})["plaintext"])


def gestionnaire():
    return GestionnaireOpenBao() if os.environ.get("GED_KMS", "local").strip().lower() == "openbao" \
        else GestionnaireLocal()


def actif():
    try:
        return gestionnaire().actif
    except ErreurChiffrement:
        return False


# ------------------------------------------------------------------ fichiers
def est_chiffre(donnees):
    return donnees[:len(MAGIQUE)] == MAGIQUE


def chiffrer(donnees, g=None):
    """Octets en clair → octets chiffrés (fichier autonome : en-tête + contenu)."""
    g = g or gestionnaire()
    cle, cle_chiffree, cle_id = g.nouvelle_cle()
    entete = json.dumps({"v": VERSION, "alg": ALGO, "kms": g.nom, "kid": cle_id, "dek": cle_chiffree},
                        separators=(",", ":"), sort_keys=True).encode()
    debut = MAGIQUE + struct.pack(">I", len(entete)) + entete
    nonce = os.urandom(12)
    contenu = AESGCM(cle).encrypt(nonce, donnees, debut)   # l'en-tête est authentifié
    del cle
    return debut + nonce + contenu


def lire_entete(donnees):
    if not est_chiffre(donnees):
        return None
    n = struct.unpack(">I", donnees[8:12])[0]
    return json.loads(donnees[12:12 + n])


def dechiffrer(donnees, g=None):
    """Octets chiffrés → octets en clair. Un ancien fichier en clair est rendu tel quel."""
    if not est_chiffre(donnees):
        return donnees
    try:
        n = struct.unpack(">I", donnees[8:12])[0]
        debut, reste = donnees[:12 + n], donnees[12 + n:]
        entete = json.loads(debut[12:])
    except (struct.error, ValueError) as e:
        raise ErreurChiffrement("En-tête de fichier chiffré illisible.") from e
    if entete.get("v") != VERSION or entete.get("alg") != ALGO:
        raise ErreurChiffrement("Format de chiffrement inconnu.")
    if g is None:
        g = GestionnaireOpenBao() if entete.get("kms") == "openbao" else GestionnaireLocal()
    cle = g.ouvrir_cle(entete["dek"], entete["kid"])
    try:
        return AESGCM(cle).decrypt(reste[:12], reste[12:], debut)
    except InvalidTag as e:
        raise ErreurChiffrement("Fichier altéré : son contenu ne correspond plus à son empreinte.") from e
