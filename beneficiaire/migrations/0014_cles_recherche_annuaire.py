# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/migrations/0014_cles_recherche_annuaire.py

from django.db import migrations, models


def calculer(apps, schema_editor):
    """Clés phonétiques et téléphoniques des usagers existants (dossiers archivés compris)."""
    from core.phonetique import chiffres, cle
    Beneficiaire = apps.get_model("beneficiaire", "Beneficiaire")
    lot = []
    for b in Beneficiaire._base_manager.all().iterator(chunk_size=500):
        b.nom_phonetique, b.prenom_phonetique, b.nom_naissance_phonetique = cle(b.nom), cle(b.prenom), cle(b.nom_naissance)
        b.telephone_mobile_cle, b.telephone_fixe_cle = chiffres(b.telephone_mobile), chiffres(b.telephone_fixe)
        lot.append(b)
        if len(lot) == 500:
            Beneficiaire._base_manager.bulk_update(lot, CHAMPS)
            lot = []
    if lot:
        Beneficiaire._base_manager.bulk_update(lot, CHAMPS)


CHAMPS = ["nom_phonetique", "prenom_phonetique", "nom_naissance_phonetique", "telephone_mobile_cle",
          "telephone_fixe_cle"]


class Migration(migrations.Migration):

    dependencies = [
        ("beneficiaire", "0013_thematiques_inclusion"),
    ]

    operations = [
        migrations.AddField(
            model_name="beneficiaire",
            name="nom_naissance_phonetique",
            field=models.CharField(
                blank=True, db_index=True, editable=False, max_length=40
            ),
        ),
        migrations.AddField(
            model_name="beneficiaire",
            name="nom_phonetique",
            field=models.CharField(
                blank=True, db_index=True, editable=False, max_length=40
            ),
        ),
        migrations.AddField(
            model_name="beneficiaire",
            name="prenom_phonetique",
            field=models.CharField(
                blank=True, db_index=True, editable=False, max_length=40
            ),
        ),
        migrations.AddField(
            model_name="beneficiaire",
            name="telephone_fixe_cle",
            field=models.CharField(
                blank=True, db_index=True, editable=False, max_length=9
            ),
        ),
        migrations.AddField(
            model_name="beneficiaire",
            name="telephone_mobile_cle",
            field=models.CharField(
                blank=True, db_index=True, editable=False, max_length=9
            ),
        ),
        migrations.RunPython(calculer, migrations.RunPython.noop),
    ]
