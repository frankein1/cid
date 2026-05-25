# Generated migration - Add accompagnant and co_intervenants fields

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('beneficiaire', '0002_initial'),
        ('planning', '0002_historique_json'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add accompagnant field (beneficiary who accompanies the main beneficiary)
        migrations.AddField(
            model_name='creneaurdv',
            name='accompagnant',
            field=models.ForeignKey(
                blank=True, 
                help_text='Personne accompagnant le bénéficiaire (ex: parent pour un mineur)', 
                null=True, 
                on_delete=django.db.models.deletion.SET_NULL, 
                related_name='rdvs_accompagnes', 
                to='beneficiaire.beneficiaire'
            ),
        ),
        
        # Add co_intervenants field (multiple social workers on same appointment)
        migrations.AddField(
            model_name='creneaurdv',
            name='co_intervenants',
            field=models.ManyToManyField(
                blank=True, 
                help_text='Autres travailleurs sociaux impliqués', 
                related_name='rdvs_partages', 
                to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
