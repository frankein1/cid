# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/migrations/0002_type_document_ged.py
from django.db import migrations


def creer_type_ru(apps, schema_editor):
    DocumentType = apps.get_model("ged", "DocumentType")
    DocumentType.objects.update_or_create(
        code="RU_PJ",
        defaults={
            "nom": "Pièce de correspondance Relation Usager",
            "categorie": "social",
            "extensions_autorisees": ["pdf"],
            "taille_max_mb": 10,
            "est_sensible": True,
            "actif": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("ged", "0001_initial"),
        ("ru", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(creer_type_ru, migrations.RunPython.noop),
    ]
