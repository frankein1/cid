# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/hashers.py
"""
Hachage des mots de passe : SEL + POIVRE.

- Le SEL (grain de sable) : Django en ajoute déjà un, aléatoire et différent
  pour chaque mot de passe, stocké avec le hachage. Rien à faire.
- Le POIVRE : un secret commun, stocké HORS de la base (variable
  d'environnement PASSWORD_PEPPER sur Render). Si la base alwaysdata fuitait
  seule, les hachages seraient inutilisables sans ce secret.

Activation : uniquement si PASSWORD_PEPPER est défini (voir settings.py).
Les anciens mots de passe restent valides : Django les re-hache avec le
poivre automatiquement à la prochaine connexion de chaque utilisateur.

⚠️ Ne JAMAIS perdre ni modifier PASSWORD_PEPPER une fois activé :
tous les mots de passe déjà poivrés deviendraient invalides.
"""

import hmac
import hashlib
import os

from django.contrib.auth.hashers import PBKDF2PasswordHasher


class PBKDF2PoivreHasher(PBKDF2PasswordHasher):
    algorithm = "pbkdf2_sha256_poivre"

    @staticmethod
    def _poivrer(password):
        poivre = os.environ.get("PASSWORD_PEPPER", "")
        if not poivre:
            raise RuntimeError("PASSWORD_PEPPER absent : impossible de vérifier un mot de passe poivré.")
        # HMAC : mélange le mot de passe et le poivre sans limite de longueur
        return hmac.new(poivre.encode(), password.encode(), hashlib.sha256).hexdigest()

    def encode(self, password, salt, iterations=None):
        return super().encode(self._poivrer(password), salt, iterations)

    def verify(self, password, encoded):
        algorithm, iterations, salt, _ = encoded.split("$", 3)
        attendu = self.encode(password, salt, int(iterations))
        return hmac.compare_digest(encoded.encode(), attendu.encode())
