# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/models/informations_preoccupantes.py

from django.db import models, transaction
from django.conf import settings
from django.utils import timezone

class NumeroCounter(models.Model):
    """Compteur simple pour générer des numéros D13-xxxxxxxx de façon atomique."""
    
    prefix = models.CharField(max_length=10, unique=True, default='D13')
    last_value = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.prefix}-{self.last_value}"

class SignalementStatus(models.TextChoices):
    NOUVEAU = "NOUVEAU", "Nouveau"
    EN_EVALUATION = "EN_EVALUATION", "En évaluation"
    A_TRANSMETTRE_PARQUET = "A_TRANSMETTRE_PARQUET", "A transmettre au Parquet"
    TRANSMIS_PARQUET = "TRANSMIS_PARQUET", "Transmis au Parquet"
    CLOS = "CLOS", "Clos"

def generate_numero(prefix='D13'):
    """Génère atomiquement un numéro D13-xxxxxxxx."""
    with transaction.atomic():
        counter, created = NumeroCounter.objects.select_for_update().get_or_create(prefix=prefix)
        counter.last_value += 1
        counter.save()
        return f"{prefix}-{counter.last_value:08d}"


class InformationPreoccupante(models.Model):
    """
    Modèle canonique d'une information préoccupante (IP).
    
    Gestion des permissions à deux niveaux :
    1. Permissions globales (via Groups Django) : qui peut accéder à l'app Protection Enfance
    2. Permissions par objet (via référents et MDS) : qui peut modifier CE dossier
    """
    
    # ==========================================================================
    # IDENTIFICATION
    # ==========================================================================
    numero = models.CharField(max_length=20, unique=True, db_index=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        verbose_name="Auteur du signalement"
    )
    
    # ==========================================================================
    # INFORMATIONS ENFANT
    # ==========================================================================
    enfant_nom = models.CharField(max_length=200, blank=True)
    enfant_date_naissance = models.DateField(null=True, blank=True)

    # ==========================================================================
    # ORIGINE ET DESCRIPTION
    # ==========================================================================
    origine_CHOICES = [
        ('MDS', 'Maison Départementale de la Solidarité'),
        ('PARTENAIRE', 'Partenaire (médecin/école/assos)'),
        ('NUM_ENFANCE', 'Numéro "enfance en danger"'),
        ('AUTRE', 'Autre'),
    ]
    origine = models.CharField(max_length=32, choices=origine_CHOICES, default='AUTRE')
    description = models.TextField()
    
    # ==========================================================================
    # GESTION DES MDS (NOUVEAU)
    # ==========================================================================
    mds_principale = models.ForeignKey(
        'mds.MDS',
        on_delete=models.PROTECT,
        related_name='ip_principale',
        verbose_name="MDS en charge du dossier",
        help_text="MDS qui gère ce dossier IP"
    )
    
    mds_partage = models.ManyToManyField(
        'mds.MDS',
        related_name='ip_partage',
        blank=True,
        verbose_name="MDS en partage",
        help_text="Autres MDS qui peuvent consulter/collaborer sur ce dossier"
    )
    
    # ==========================================================================
    # BINÔME RÉFÉRENT (NOUVEAU)
    # ==========================================================================
    referent_1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ip_referent_1',
        verbose_name="Référent 1",
        help_text="Premier référent du dossier (binôme)"
    )
    
    referent_2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ip_referent_2',
        verbose_name="Référent 2",
        help_text="Second référent du dossier (binôme)"
    )
    
    # ==========================================================================
    # STATUT ET DATES
    # ==========================================================================
    date_creation = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(
        max_length=32, 
        choices=SignalementStatus.choices, 
        default=SignalementStatus.NOUVEAU
    )
    transmit_parquet = models.BooleanField(default=False)
    transmis_parquet_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-date_creation',)
        verbose_name = "Information Préoccupante"
        verbose_name_plural = "Informations Préoccupantes"
        permissions = [
            ("instruire_ip", "Peut instruire une IP"),
            ("transmettre_parquet", "Peut transmettre au Parquet"),
        ]

    def __str__(self):
        return f"{self.numero} - {self.enfant_nom or 'ND'}"

    @classmethod
    def create_with_numero(cls, **kwargs):
        """Facade de création : génère numéro si absent."""
        if 'numero' not in kwargs or not kwargs['numero']:
            kwargs['numero'] = generate_numero(prefix='D13')
        return cls.objects.create(**kwargs)
    
    # ==========================================================================
    # MÉTHODES DE VÉRIFICATION DES PERMISSIONS (NIVEAU OBJET)
    # ==========================================================================
    
    def est_referent(self, user):
        """Vérifie si l'utilisateur est référent de ce dossier."""
        return user == self.referent_1 or user == self.referent_2
    
    def appartient_a_mds(self, user):
        """Vérifie si l'utilisateur appartient à la MDS en charge ou en partage."""
        if not user.mds_principale:
            return False
        
        # MDS principale
        if user.mds_principale == self.mds_principale:
            return True
        
        # MDS en partage
        if self.mds_partage.filter(id=user.mds_principale.id).exists():
            return True
        
        return False
    
    def peut_voir(self, user):
        """
        Vérifie si l'utilisateur peut VOIR ce dossier.
        
        Logique :
        1. Doit avoir la permission globale view_informationpreoccupante
        2. ET l'une des conditions suivantes :
           - Est référent du dossier
           - Appartient à la MDS en charge ou en partage
           - Est cadre/direction (voit tout)
        """
        # Permission globale obligatoire
        if not user.has_perm('protection_enfance.view_informationpreoccupante'):
            return False
        
        # Direction : voit tout
        if user.groups.filter(name__in=['DITAS_Direction', 'DGAS_Direction']).exists():
            return True
        
        # Référent : voit son dossier
        if self.est_referent(user):
            return True
        
        # Appartient à la MDS
        if self.appartient_a_mds(user):
            return True
        
        return False
    
    def peut_modifier(self, user):
        """
        Vérifie si l'utilisateur peut MODIFIER ce dossier.
        
        Logique :
        1. Doit avoir la permission globale change_informationpreoccupante
        2. ET l'une des conditions suivantes :
           - Est référent du dossier
           - Est cadre de la MDS en charge
           - Est direction (modifie tout)
        """
        # Permission globale obligatoire
        if not user.has_perm('protection_enfance.change_informationpreoccupante'):
            return False
        
        # Direction : modifie tout
        if user.groups.filter(name__in=['DITAS_Direction', 'DGAS_Direction']).exists():
            return True
        
        # Cadre de la MDS principale
        if user.groups.filter(name='MDS_Cadres').exists():
            if user.mds_principale == self.mds_principale:
                return True
        
        # Référent du dossier
        if self.est_referent(user):
            return True
        
        return False
    
    def peut_transmettre_parquet(self, user):
        """
        Vérifie si l'utilisateur peut transmettre au Parquet.
        
        Logique : Cadres et Direction uniquement
        """
        if not user.has_perm('protection_enfance.transmettre_parquet'):
            return False
        
        # Uniquement cadres et direction
        if user.groups.filter(name__in=['MDS_Cadres', 'DITAS_Direction', 'DGAS_Direction']).exists():
            # Si cadre, doit être de la MDS principale
            if user.groups.filter(name='MDS_Cadres').exists():
                return user.mds_principale == self.mds_principale
            return True
        
        return False
    
    def get_niveau_acces(self, user):
        """
        Retourne le niveau d'accès de l'utilisateur sur ce dossier.
        Utile pour l'affichage dans les templates.
        
        Returns:
            str: 'aucun', 'lecture', 'ecriture', 'complet'
        """
        if not self.peut_voir(user):
            return 'aucun'
        
        if self.peut_transmettre_parquet(user):
            return 'complet'
        
        if self.peut_modifier(user):
            return 'ecriture'
        
        return 'lecture'


class HistoriqueAction(models.Model):
    """Journalise les actions effectuées sur une IP."""
    
    information = models.ForeignKey(
        InformationPreoccupante, 
        related_name='historique_actions', 
        on_delete=models.CASCADE
    )
    action = models.CharField(max_length=200)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL
    )
    commentaire = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-date',)
        verbose_name = "Historique d'action"
        verbose_name_plural = "Historiques d'actions"
    
    def __str__(self):
        return f"{self.information.numero} - {self.action} - {self.date}"
