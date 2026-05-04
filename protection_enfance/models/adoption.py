# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/models/adoption.py

class ProcedureAdoption(models.Model):
    """Procédure d'adoption complète"""
    
    TYPES_ADOPTION = [
        ('SIMPLE', 'Adoption simple'),
        ('PLENIERE', 'Adoption plénière'),
        ('INTERNATIONALE', 'Adoption internationale'),
    ]
    
    # Enfant
    enfant = models.ForeignKey('beneficiaires.Usager', on_delete=models.PROTECT)
    situation_avant_adoption = models.TextField()
    
    # Parents adoptifs
    parents_adoptifs = models.ManyToManyField('beneficiaires.Usager', related_name='adoptions')
    agrement_adoption = models.CharField(max_length=100, blank=True)
    
    # Procédure
    type_adoption = models.CharField(max_length=50, choices=TYPES_ADOPTION)
    date_depot_demande = models.DateField()
    date_jugement = models.DateField(null=True, blank=True)
    tribunal = models.CharField(max_length=200, blank=True)
    
    # Suivi post-adoption
    suivi_post_adoption = models.BooleanField(default=False)
    frequence_suivi = models.CharField(max_length=50, blank=True)
    date_fin_suivi = models.DateField(null=True, blank=True)

class AgrementAdoption(models.Model):
    """Agrément pour adoption"""
    
    demandeurs = models.ManyToManyField('beneficiaires.Usager', related_name='agrements_adoption')
    numero_agrement = models.CharField(max_length=50, unique=True)
    date_debut = models.DateField()
    date_fin = models.DateField()
    statut = models.CharField(max_length=20, choices=[
        ('EN_COURS', 'En cours d\'instruction'),
        ('ACCORDE', 'Accordé'),
        ('REFUSE', 'Refusé'),
        ('RENOUVELE', 'Renouvelé'),
    ])
