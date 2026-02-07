# protection_enfance/management/commands/migrate_signalements_crip.py
from django.core.management.base import BaseCommand
from protection_enfance.models.signalements import SignalementCRIP
from protection_enfance.models.informations_preoccupantes import InformationPreoccupante, HistoriqueAction


class Command(BaseCommand):
help = "Migrer SignalementCRIP -> InformationPreoccupante"


def handle(self, *args, **options):
total = SignalementCRIP.objects.count()
self.stdout.write(f"Migration de {total} signalements CRIP")
for s in SignalementCRIP.objects.all():
ip = InformationPreoccupante.create_with_numero(
auteur = getattr(s, 'auteur', None),
enfant_nom = getattr(s, 'enfant_nom', '') or getattr(s, 'nom_enfant', ''),
enfant_date_naissance = getattr(s, 'enfant_date_naissance', None),
origine = 'PARTENAIRE' if getattr(s, 'auteur', '') else 'AUTRE',
description = getattr(s, 'detail', '') or getattr(s, 'description', ''),
)
HistoriqueAction.objects.create(
information=ip,
action="Migré depuis SignalementCRIP",
commentaire=f"Origine id {s.pk}"
)
self.stdout.write(f"Migré {s.pk} -> {ip.numero}")
self.stdout.write("Terminé")
