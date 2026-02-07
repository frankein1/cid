# protection_enfance/models/placements/base.py

class Placement(models.Model):
    """Modèle de base pour tous les types de placement"""
    
    TYPES_PLACEMENT = [
        ('FAMILLE_ACCUEIL', 'Famille d\'accueil'),
        ('MEF', 'Maison d\'Enfants à Caractère Social'),
        ('DOMICILE', 'À domicile'),
        ('TIERS_CONFIANCE', 'Tiers digne de confiance'),
        ('AEMO', 'AEMO avec hébergement'),
    ]
    
    # Enfant
    enfant = models.ForeignKey('beneficiaires.Usager', on_delete=models.PROTECT)
    decision_placement = models.ForeignKey('DecisionPlacement', on_delete=models.PROTECT)
    
    # Période
    date_debut = models.DateField()
    date_fin_prevue = models.DateField(null=True, blank=True)
    date_fin_reelle = models.DateField(null=True, blank=True)
    
    # Type et lieu
    type_placement = models.CharField(max_length=50, choices=TYPES_PLACEMENT)
    lieu_placement = models.ForeignKey('LieuPlacement', on_delete=models.PROTECT)
    
    # Cadre juridique
    cadre_juridique = models.CharField(max_length=100)  # AGO, JDE, etc.
    numero_decision = models.CharField(max_length=100)
    
    # Suivi
    referent_ase = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='placements_referes')
    educateur_referent = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Statut
    statut = models.CharField(max_length=20, choices=[
        ('PROJET', 'Projet de placement'),
        ('EN_COURS', 'En cours'),
        ('TERMINE', 'Terminé'),
        ('RUPTURE', 'Rupture anticipée'),
    ])
