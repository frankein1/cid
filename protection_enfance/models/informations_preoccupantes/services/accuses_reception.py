# protection_enfance/informations_preoccupantes/services/accuses_reception.py

class ServiceAccusesReception:
    """Gestion des accusés de réception sous 24h"""
    
    def envoyer_accuse_reception(self, information_preoccupante):
        """Envoie l'accusé de réception sous 24h"""
        
        if information_preoccupante.date_accuse_reception:
            return  # Déjà envoyé
        
        # Générer l'accusé de réception
        template_data = {
            'numero_ip': information_preoccupante.numero_signalement,
            'date_reception': information_preoccupante.date_reception,
            'mineur_nom': information_preoccupante.mineur.nom_complet,
            'crip_contact': "04 13 31 80 80 - crip@departement13.fr",
        }
        
        # Utiliser le moteur d'édition
        from editions.services import GenerateurDocuments
        accusé = GenerateurDocuments.generer_document(
            'accuse_reception_ip',
            template_data
        )
        
        # Envoyer par email si signalant professionnel
        if information_preoccupante.signalant_email:
            self._envoyer_email_accuse(information_preoccupante, accusé)
        
        information_preoccupante.date_accuse_reception = timezone.now()
        information_preoccupante.save()
