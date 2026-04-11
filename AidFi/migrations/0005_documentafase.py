# Generated manually for DocumentAFASE model
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ged', '0001_initial'),  # Vérifie la dernière migration de ged
        ('AidFi', '0004_add_decide_par.py'),  # Remplace par ta dernière migration AidFi
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentAFASE',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('type_document', models.CharField(choices=[('IDENTITE', 'Identité'), ('RIB', 'RIB'), ('JUSTIFICATIF', 'Justificatif'), ('FACTURE', 'Facture'), ('AUTRE', 'Autre')], max_length=20)),
                ('obligatoire', models.BooleanField(default=False)),
                ('date_ajout', models.DateTimeField(auto_now_add=True)),
                ('demande', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents_afase', to='AidFi.demandeafase')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='afase_documents', to='ged.documentged')),
            ],
            options={
                'verbose_name': 'Document AFASE',
                'verbose_name_plural': 'Documents AFASE',
                'ordering': ['type_document', '-date_ajout'],
                'unique_together': {('demande', 'document')},
            },
        ),
    ]
