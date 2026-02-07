# protection_enfance/informations_preoccupantes/models/signalements.py

class SignalementCRIP(models.Model):
    """Signalement conforme au processus CD13"""
    
    # Identification
    numero_signalement = models.CharField(max_length=20, unique=True)  # Format: IP-2024-001234
    date_reception = models.DateTimeField(auto_now_add=True)
    
    # Origine (conforme aux catégories du guide)
    ORIGINES = [
        ('PROFESSIONNEL', 'Professionnel'),
        ('PARTICULIER', 'Particulier'),
        ('SIGNALEMENT_AUTO', 'Signalement automatique'),
        ('AUTRE_SERVICE', 'Autre service départemental'),
    ]
    origine = models.CharField(max_length=50, choices=ORIGINES)
    
    # Signalant (si professionnel)
    signalant_nom = models.CharField(max_length=100, blank=True)
    signalant_qualite = models.CharField(max_length=100, blank=True)
    signalant_structure = models.CharField(max_length=200, blank=True)
    signalant_contact = models.TextField(blank=True)
    
    # Confidentialité
    confidentialite_signalant = models.BooleanField(
        default=False,
        verbose_name="Signalant demande la confidentialité"
    )
