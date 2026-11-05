# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ged/management/commands/cle_ged.py
"""
Tire au hasard une clé maîtresse pour le chiffrement de la GED (32 octets, en base64), à recopier dans la
variable d'environnement GED_CLE_MAITRESSE du serveur. La clé n'est enregistrée nulle part par CID.

    python manage.py cle_ged
"""
import base64
import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Génère une clé maîtresse pour GED_CLE_MAITRESSE (chiffrement de la GED)."

    def handle(self, *args, **opts):
        self.stdout.write(base64.b64encode(os.urandom(32)).decode())
        self.stderr.write("⚠️ Recopiez-la dans GED_CLE_MAITRESSE et SAUVEGARDEZ-LA hors de CID : "
                          "sans elle, les fichiers chiffrés sont définitivement illisibles.")
