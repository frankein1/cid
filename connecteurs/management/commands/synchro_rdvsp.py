# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/management/commands/synchro_rdvsp.py
"""
Synchronise l'agenda CID avec RDV-Solidarités (publication, prolongation, retraits, blocages), prépare et
envoie les invitations du mois quand c'est l'heure, et efface
le contenu des avis de plus de 30 jours. À planifier chaque nuit en production ; sur la démo, CID la lance
aussi d'elle-même au plus une fois par jour, à la première connexion.

    python manage.py synchro_rdvsp
"""
from django.core.management.base import BaseCommand, CommandError

from connecteurs import rdvsp_synchro as sync


class Command(BaseCommand):
    help = "Synchronise l'agenda CID avec RDV-Solidarités."

    def handle(self, *args, **opts):
        if not sync.prete():
            raise CommandError("Passerelle RDV-Solidarités non activée ou compte de synchronisation non relié.")
        b = sync.synchroniser()
        n = sync.purger_avis()
        from connecteurs import rdvsp_invitations
        inv = rdvsp_invitations.traiter()
        if inv:
            self.stdout.write(f"Invitations : {inv}")
        self.stdout.write(self.style.SUCCESS(
            f"{b['publiees']} publiée(s), {b['prolongees']} prolongée(s), {b['neutralisees']} retirée(s), "
            f"{b['blocages']} blocage(s) ; {n} avis purgé(s)."))
        for e in b["erreurs"]:
            self.stderr.write(f"⚠️ {e}")
