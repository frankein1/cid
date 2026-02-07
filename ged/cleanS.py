from django.core.management.base import BaseCommand
from ged.models import DocumentVersion
from ged.storage import SeaweedFSStorage


class Command(BaseCommand):
    help = "Nettoyage SeaweedFS (fichiers GED orphelins)"

    def handle(self, *args, **options):
        storage = SeaweedFSStorage()

        used_ids = set(
            DocumentVersion.objects.values_list("seaweedfs_id", flat=True)
        )

        try:
            all_ids = storage.list_all_file_ids()
        except NotImplementedError:
            self.stderr.write(
                "list_all_file_ids non implémenté côté SeaweedFS"
            )
            return

        for fid in all_ids - used_ids:
            storage.delete(fid)
            self.stdout.write(f"Supprimé : {fid}")
