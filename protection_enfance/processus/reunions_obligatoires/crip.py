# protection_enfance/reunions_obligatoires/crip.py

class ReunionCRIP(models.Model):
    """Réunion de la Cellule de Recueil des Informations Préoccupantes"""
    
    date_reunion = models.DateTimeField()
    participants = models.ManyToManyField('core.User', related_name='reunions_crip')
    ordre_du_jour = models.TextField()
    
    # IPs à examiner
    ips_a_traiter = models.ManyToManyField('InformationPreoccupante', related_name='reunions_crip')
    
    # Décisions
    decisions = models.JSONField(default=list)  # {ip_id: decision, motifs, delai}
    
    # Intégration calendrier
    evenement_calendrier_id = models.CharField(max_length=255, blank=True)  # ID Outlook
    lien_visio = models.URLField(blank=True)
    
    class Meta:
        verbose_name = "Réunion CRIP"

class GestionnaireCalendrier:
    """Intégration avec Outlook/iCal"""
    
    def creer_evenement_calendrier(self, reunion, utilisateurs):
        """Crée un événement dans les calendriers Outlook des participants"""
        
        # Format iCal
        evenement_ical = f"""
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Réunion CRIP - {reunion.date_reunion.strftime('%d/%m/%Y')}
DTSTART:{reunion.date_reunion.strftime('%Y%m%dT%H%M%S')}
DTEND:{(reunion.date_reunion + timedelta(hours=2)).strftime('%Y%m%dT%H%M%S')}
DESCRIPTION:{reunion.ordre_du_jour}
LOCATION:Salle réunion CRIP - DITAS
END:VEVENT
END:VCALENDAR
        """
        
        # Pour chaque participant, ajouter à son calendrier Outlook
        for utilisateur in utilisateurs:
            if utilisateur.email:
                self._envoyer_invitation_outlook(utilisateur.email, evenement_ical)
        
        return True
    
    def _envoyer_invitation_outlook(self, email, evenement_ical):
        """Envoie l'invitation Outlook (à intégrer avec l'API Microsoft Graph)"""
        # Implémentation avec Microsoft Graph API
        pass
