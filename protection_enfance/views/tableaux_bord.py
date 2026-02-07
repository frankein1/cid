# protection_enfance/informations_preoccupantes/views/tableaux_bord.py

class TableauBordCRIPView:
    """Tableau de bord spécifique pour la CRIP CD13"""
    
    def get_indicateurs_cles(self):
        return {
            'signalements_24h': self._get_signalements_24h(),
            'accuses_en_retard': self._get_accuses_en_retard(),
            'ips_en_analyse': self._get_ips_en_analyse(),
            'transmissions_parquet': self._get_transmissions_parquet(),
            'delais_moyens_traitement': self._get_delais_moyens(),
        }
    
    def _get_accuses_en_retard(self):
        """Retourne les IP sans accusé après 24h"""
        seuil_24h = timezone.now() - timedelta(hours=24)
        return InformationPreoccupante.objects.filter(
            date_accuse_reception__isnull=True,
            date_reception__lt=seuil_24h
        ).count()
