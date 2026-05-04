# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/delais/alertes_delais.py

class SystemeAlertes:
    """Gestion des alertes de délais et obligations"""
    
    def verifier_alertes_obligatoires(self):
        alertes = []
        
        # Alertes IP
        alertes.extend(self._verifier_delais_ip())
        
        # Alertes placements
        alertes.extend(self._verifier_rapports_annuels())
        
        # Alertes réunions
        alertes.extend(self._verifier_reunions_obligatoires())
        
        return alertes
    
    def _verifier_delais_ip(self):
        ips_en_retard = InformationPreoccupante.objects.filter(
            statut='EN_COURS',
            date_reception__lt=timezone.now() - timedelta(days=15)
        )
        
        return [
            {
                'type': 'DELAI_IP_DEPASSE',
                'gravite': 'HAUTE',
                'message': f"IP {ip.numero_ip} en retard de traitement",
                'lien': f"/protection_enfance/ip/{ip.id}/",
                'action_requise': 'Traiter urgemment'
            }
            for ip in ips_en_retard
        ]
    
    def _verifier_rapports_annuels(self):
        aujourdhui = timezone.now().date()
        placements_actifs = Placement.objects.filter(statut='EN_COURS')
        
        alertes = []
        for placement in placements_actifs:
            if placement.date_debut:
                # Rapport annuel dû
                if (aujourdhui - placement.date_debut).days >= 365:
                    dernier_rapport = placement.rapports.filter(
                        type_rapport='ANNUEL'
                    ).order_by('-date_rapport').first()
                    
                    if not dernier_rapport or (aujourdhui - dernier_rapport.date_rapport).days >= 365:
                        alertes.append({
                            'type': 'RAPPORT_ANNUEL_DU',
                            'gravite': 'MOYENNE',
                            'message': f"Rapport annuel dû pour {placement.enfant.nom_complet}",
                            'lien': f"/protection_enfance/placement/{placement.id}/rapport/",
                            'action_requise': 'Rédiger rapport annuel'
                        })
        
        return alertes
