# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/models/mesures_educatives.py

class MesureEducative(models.Model):
    """Mesure éducative (AEMO, AED, etc.)"""
    
    TYPES_MESURE = [
        ('AEMO', 'Action Éducative en Milieu Ouvert'),
        ('AED', 'Aide Éducative à Domicile'),
        ('AES', 'Accompagnement Éducatif Spécialisé'),
        ('SPJ', 'Service de Prévention Spécialisée'),
    ]
    
    enfant = models.ForeignKey('beneficiaires.Usager', on_delete=models.PROTECT)
    type_mesure = models.CharField(max_length=50, choices=TYPES_MESURE)
    date_debut = models.DateField()
    date_fin_prevue = models.DateField(null=True, blank=True)
    
    # Cadre juridique
    decision = models.CharField(max_length=200)  # Référence décision
    service_executant = models.ForeignKey('core.Service', on_delete=models.PROTECT)
    
    # Objectifs
    objectifs = models.TextField()
    modalites_intervention = models.TextField()
    
    # Évaluation
    evaluations = models.JSONField(default=list)  # Évaluations périodiques
