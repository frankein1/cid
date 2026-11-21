# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/migrations/0016_cles_ville_adresse.py
"""Clés de recherche de la ville et de l'adresse (sans accents, sans tirets ni espaces, en minuscules) : « Port-de-Bouc »,
« port de bouc » et « portdebouc » donnent la même clé. Remplies pour les usagers existants."""
import unicodedata
import re

from django.db import migrations, models


def norme(texte):
    t = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", t.lower())


def remplir(apps, schema_editor):
    B = apps.get_model("beneficiaire", "Beneficiaire")
    lot = []
    for b in B.objects.only("pk", "ville", "adresse").iterator():
        b.ville_cle, b.adresse_cle = norme(b.ville)[:120], norme(b.adresse)
        lot.append(b)
        if len(lot) >= 500:
            B.objects.bulk_update(lot, ["ville_cle", "adresse_cle"])
            lot = []
    if lot:
        B.objects.bulk_update(lot, ["ville_cle", "adresse_cle"])


class Migration(migrations.Migration):
    dependencies = [("beneficiaire", "0015_notes_personnelles")]

    operations = [
        migrations.AddField(model_name="beneficiaire", name="ville_cle",
                            field=models.CharField(max_length=120, blank=True, editable=False, db_index=True, default=""),
                            preserve_default=False),
        migrations.AddField(model_name="beneficiaire", name="adresse_cle",
                            field=models.TextField(blank=True, editable=False, default=""),
                            preserve_default=False),
        migrations.RunPython(remplir, migrations.RunPython.noop),
    ]
