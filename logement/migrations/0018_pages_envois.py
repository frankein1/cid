# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/migrations/0018_pages_envois.py
import csv
from pathlib import Path

from django.db import migrations, models

CSV = Path(__file__).resolve().parent.parent / 'donnees' / 'pages_envois.csv'


def charger_csv(apps, schema_editor):
    """Charge le minimum de pages par type de dossier depuis logement/donnees/pages_envois.csv."""
    Regle = apps.get_model('logement', 'ReglePagesEnvoi')
    with open(CSV, encoding='utf-8', newline='') as f:
        for ligne in csv.DictReader(f, delimiter=';'):
            Regle.objects.update_or_create(code=ligne['code'].strip(), defaults={
                'libelle': ligne['libelle'].strip(),
                'pages_dossier': int(ligne['pages_dossier']),
                'pages_pieces_jointes': int(ligne['pages_pieces_jointes']),
            })


class Migration(migrations.Migration):
    dependencies = [('logement', '0017_recours_dalo_ressources_lieux')]

    operations = [
        migrations.AddField(model_name='envoidossier', name='pages_dossier',
                            field=models.PositiveIntegerField(default=0, help_text="Pages du dossier lui-même (minimum du CSV ou réel)")),
        migrations.AddField(model_name='envoidossier', name='pages_pieces',
                            field=models.PositiveIntegerField(default=0, help_text="Pages des pièces jointes (minimum du CSV ou réel)")),
        migrations.AlterField(model_name='envoidossier', name='pages',
                              field=models.PositiveIntegerField(default=0, help_text="Total compté : dossier + pièces jointes")),
        migrations.CreateModel(
            name='ReglePagesEnvoi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(help_text="Ex. AFASE, FSL, COPP", max_length=40, unique=True)),
                ('libelle', models.CharField(max_length=160)),
                ('pages_dossier', models.PositiveIntegerField(default=0)),
                ('pages_pieces_jointes', models.PositiveIntegerField(default=0)),
            ],
            options={'verbose_name': 'Minimum de pages par type de dossier', 'ordering': ['code']},
        ),
        migrations.RunPython(charger_csv, migrations.RunPython.noop),
    ]
