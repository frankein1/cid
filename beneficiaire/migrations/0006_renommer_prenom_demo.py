# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/migrations/0006_renommer_prenom_demo.py
"""
Données fictives de démonstration (init2) : l'enfant « Leo » de la famille RECOMP devient « Sacha »
(prénom à ne pas utiliser dans les données fictives). Le code interne suit (FAM2-LEO → FAM2-SAC)
pour que init2 retrouve la fiche au lieu d'en créer une nouvelle. Les copies du prénom dans les IP
sont mises à jour. Aucune autre donnée n'est touchée.
"""
from django.db import migrations


def renommer(apps, schema_editor):
    Beneficiaire = apps.get_model('beneficiaire', 'Beneficiaire')
    EnfantIP = apps.get_model('protection_enfance', 'EnfantIP')
    for b in Beneficiaire.objects.filter(code_interne='FAM2-LEO', nom='RECOMP', prenom='Leo'):
        nouveau = 'FAM2-SAC' if not Beneficiaire.objects.filter(code_interne='FAM2-SAC').exists() else b.code_interne
        Beneficiaire.objects.filter(pk=b.pk).update(prenom='Sacha', code_interne=nouveau)
        EnfantIP.objects.filter(beneficiaire_id=b.pk, prenom='Leo').update(prenom='Sacha')


class Migration(migrations.Migration):
    dependencies = [
        ('beneficiaire', '0005_beneficiaire_code_insee_naissance_and_more'),
        ('protection_enfance', '0001_circuit_ip'),
    ]
    operations = [migrations.RunPython(renommer, migrations.RunPython.noop)]
