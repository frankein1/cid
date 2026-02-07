# protection_enfance/processus/informations_preoccupantes/evaluations_sociales.py

class EnqueteSociale(models.Model):
    """Enquête sociale complète"""
    
    information_preoccupante = models.OneToOneField('InformationPreoccupante', on_delete=models.CASCADE)
    evaluateur = models.ForeignKey('core.User', on_delete=models.PROTECT)
    
    # Entretiens réalisés
    entretiens_famille = models.JSONField(default=list)
    auditions_enfant = models.JSONField(default=list)
    contacts_partenaires = models.JSONField(default=list)
    
    # Analyse
    situation_familiale = models.TextField()
    conditions_vie = models.TextField()
    relations_familiales = models.TextField()
    besoins_enfant = models.TextField()
    
    # Recommandations
    recommandations = models.TextField()
    urgence_mesure = models.BooleanField(default=False)
    type_mesure_proposee = models.CharField(max_length=50, choices=[
        ('AEMO', 'AEMO'),
        ('PLACEMENT', 'Placement'),
        ('AED', 'AED'),
        ('CLASSE', 'Classement sans suite'),
    ])
    
    # Validation
    date_validation = models.DateField(null=True, blank=True)
    valide_par = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, related_name='enquetes_validees')
    
    # Documents générés
    rapport_enquete = models.ForeignKey('ged.Document', on_delete=models.SET_NULL, null=True)
    synthese_transmission = models.ForeignKey('ged.Document', on_delete=models.SET_NULL, null=True, related_name='synthese_enquete')

class ModeleRapport:
    """Générateur de rapports automatisés"""
    
    def generer_rapport_annuel(self, placement):
        """Génère le rapport annuel de situation"""
        
        donnees = {
            'enfant': placement.enfant,
            'placement': placement,
            'bilan_sante': self._get_bilan_sante(placement),
            'bilan_scolaire': self._get_bilan_scolaire(placement),
            'bilan_psychologique': self._get_bilan_psychologique(placement),
            'evolution_familiale': self._get_evolution_familiale(placement),
            'projet_avenir': self._get_projet_avenir(placement),
        }
        
        # Utilisation du moteur de template d'édition
        from editions.utils import generateur_documents
        return generateur_documents.generer_document('rapport_annuel_ase', donnees)
