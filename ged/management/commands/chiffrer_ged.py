# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ged/management/commands/chiffrer_ged.py
"""
Chiffre les fichiers de la GED déposés avant l'activation du chiffrement (ged/chiffrement.py).

Pour chaque fichier encore en clair : lecture, dépôt d'une copie chiffrée (nouvel identifiant), mise à jour
des références en base, puis suppression de l'ancien fichier. Un fichier déjà chiffré n'est pas retouché.
Peut être relancée sans risque (elle reprend là où elle s'est arrêtée).

    python manage.py chiffrer_ged --essai     # compte sans rien modifier
    python manage.py chiffrer_ged
"""
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ged import chiffrement
from ged.models import DocumentGED, DocumentVersion
from ged.storage import SeaweedFSStorage


class Command(BaseCommand):
    help = "Chiffre les fichiers de la GED encore stockés en clair."

    def add_arguments(self, parser):
        parser.add_argument("--essai", action="store_true", help="Compter seulement, sans rien modifier.")
        parser.add_argument("--max", type=int, default=0, help="Nombre maximum de fichiers à chiffrer (0 = tous).")

    def handle(self, *args, **opts):
        if not chiffrement.actif():
            raise CommandError("Aucune clé de chiffrement configurée (voir docs/CHIFFREMENT_GED.md).")
        storage = SeaweedFSStorage()
        fids = set(DocumentVersion.objects.values_list("seaweedfs_id", flat=True)) | \
            set(DocumentGED.objects.exclude(seaweedfs_id__isnull=True).exclude(seaweedfs_id="")
                .values_list("seaweedfs_id", flat=True))
        deja = clair = absents = erreurs = restants = 0
        for fid in sorted(f for f in fids if f):
            try:
                donnees = storage.open_brut(fid)
            except Exception:
                absents += 1
                continue
            if chiffrement.est_chiffre(donnees):
                deja += 1
                continue
            if opts["max"] and clair >= opts["max"]:
                restants += 1
                continue
            clair += 1
            if opts["essai"]:
                continue
            try:
                # Nom neutre : il ne doit pas contenir l'ancien identifiant (la suppression de l'ancien
                # fichier, en stockage temporaire, se fait par recherche du nom)
                ext = (DocumentVersion.objects.filter(seaweedfs_id=fid).values_list("extension", flat=True).first()
                       or DocumentGED.objects.filter(seaweedfs_id=fid).values_list("extension", flat=True).first() or "")
                nom = f"document.{ext}" if ext else "document"
                nouveau = storage.save(nom, ContentFile(donnees, name=nom))  # _save chiffre
                if storage.open(nouveau).read() != donnees:                  # relecture de contrôle
                    raise CommandError("relecture différente")
                with transaction.atomic():
                    DocumentVersion.objects.filter(seaweedfs_id=fid).update(seaweedfs_id=nouveau)
                    DocumentGED.objects.filter(seaweedfs_id=fid).update(seaweedfs_id=nouveau)
                storage.delete(fid)
            except Exception as e:
                erreurs += 1
                self.stderr.write(f"❌ {fid} : {e}")
        verbe = "à chiffrer" if opts["essai"] else "chiffrés"
        self.stdout.write(self.style.SUCCESS(
            f"{clair} fichier(s) {verbe}, {deja} déjà chiffré(s), {absents} introuvable(s), {erreurs} erreur(s)"
            + (f", {restants} restant(s) : relancer." if restants else ".")))
