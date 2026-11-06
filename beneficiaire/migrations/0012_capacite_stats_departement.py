# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/migrations/0012_capacite_stats_departement.py
"""Capacité « stats_departement » (statistiques de l'accompagnement de tout le département), donnée aux profils de
direction s'ils existent. Faite en migration pour que le serveur l'ait sans lancer init_profils."""
from django.db import migrations

CODE = "stats_departement"
NOM = "Statistiques de l'accompagnement de tout le département (comparaison des MDS, sans détail par agent)"


def creer(apps, schema_editor):
    Capacite = apps.get_model("core", "Capacite")
    Profil = apps.get_model("core", "Profil")
    cap, _ = Capacite.objects.get_or_create(code=CODE, defaults={"nom": NOM, "actif": True})
    for p in Profil.objects.filter(code__in=["DIR_DIRECTION", "DIR_CADRE"]):
        p.capacites.add(cap)


class Migration(migrations.Migration):
    dependencies = [("beneficiaire", "0011_journal_accompagnement"), ("core", "0006_journal_activite")]
    operations = [migrations.RunPython(creer, migrations.RunPython.noop)]
