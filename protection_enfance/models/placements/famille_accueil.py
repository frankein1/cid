# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/models/placements/famille_accueil.py

class FamilleAccueil(models.Model):
    """Famille d'accueil agréée"""
    
    agrement = models.CharField(max_length=50, unique=True)
    date_agrement = models.DateField()
    date_fin_agrement = models.DateField()
    
    # Capacité d'accueil
    nombre_places = models.PositiveIntegerField()
    ages_acceptes = models.JSONField()  # Ex: {"min": 0, "max": 18}
    specificites = models.JSONField(default=list)  # Handicap, fratrie, etc.
    
    # Contact
    adresse = models.TextField()
    telephone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    
    # Statut
    statut_agrement = models.CharField(max_length=20, choices=[
        ('ACTIF', 'Actif'),
        ('SUSPENDU', 'Suspendu'),
        ('RETIRE', 'Retiré'),
        ('EN_COURS', 'En cours d\'agrément'),
    ])

class PlacementFamilleAccueil(Placement):
    """Placement spécifique en famille d'accueil"""
    
    famille = models.ForeignKey(FamilleAccueil, on_delete=models.PROTECT)
    assistant_familial = models.ForeignKey('core.User', on_delete=models.PROTECT)
    
    # Spécificités
    projet_accueil = models.FileField(upload_to='projets_accueil/', null=True, blank=True)
    contacts_parents = models.JSONField(default=dict)  # Fréquence, modalités
    scolarite = models.TextField(blank=True)  # École, transport
