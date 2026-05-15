# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# planning/models.py
"""
PLANNING MODELS – VERSION UNIFIÉE (V2 + RÉCUPÉRATION V1)
Fusion effectuée :
- Sécurité V2 : Verrous SQL (select_for_update), transactions atomiques.
- Règles V2 : Horaires stricts (09h00 - 17h00).
- Restauration V1 : Modèles JourBloque et ConfigurationPlanning.
- Restauration V1 : Méthodes de confort (est_passe, get_duree_affichage).
"""

from datetime import time, datetime
from django.db import models, transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

# Import spécifique pour les capacités
from mds.models import UserMDSProfile, HoraireMDS

# =============================================================================
# MODÈLE CONFIGURATION (Restauration V1)
# =============================================================================

class ConfigurationPlanning(models.Model):
    """Configuration globale du planning"""
    cle = models.CharField(max_length=100, unique=True)
    valeur = models.TextField()
    type_valeur = models.CharField(
        max_length=20,
        choices=[
            ('STRING', 'Chaîne'),
            ('INTEGER', 'Entier'),
            ('BOOLEAN', 'Booléen'),
            ('JSON', 'JSON'),
            ('TIME', 'Heure'),
        ]
    )
    description = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['cle']
    
    def __str__(self):
        return f"{self.cle} = {self.valeur}"
    
    @classmethod
    def get_valeur(cls, cle, default=None):
        """Récupère une valeur avec conversion de type"""
        try:
            config = cls.objects.get(cle=cle)
            if config.type_valeur == 'INTEGER':
                return int(config.valeur)
            elif config.type_valeur == 'BOOLEAN':
                return config.valeur.lower() in ('true', '1', 'yes', 'oui')
            elif config.type_valeur == 'JSON':
                import json
                return json.loads(config.valeur)
            elif config.type_valeur == 'TIME':
                try:
                    return datetime.strptime(config.valeur, '%H:%M').time()
                except ValueError:
                    return default
            return config.valeur
        except cls.DoesNotExist:
            return default


# =============================================================================
# MODÈLE CRÉNEAU (Version V2 sécurisée)
# =============================================================================

class CreneauRdv(models.Model):
    TYPE_RDV_CHOICES = [
        ('PERMANENCE', 'Permanence'),
        ('IP', 'Information préoccupante'),
        ('ENFANCE', 'Enfance'),
        ('HORS_PERMANENCE', 'Hors permanence'),
        ('TELEPHONIQUE', 'Téléphonique'),
        ('VISITE_DOMICILE', 'Visite à domicile'),
        ('REUNION', 'Réunion'),
        ('FORMATION', 'Formation'),
        ('ADMINISTRATIF', 'Administratif'),
    ]

    STATUT_RDV_CHOICES = [
        ('DISPONIBLE', 'Disponible'),
        ('RESERVE', 'Réservé'),
        ('VENU_RECU', 'Venu et reçu'),
        ('VENU_NON_RECU', 'Venu non reçu'),
        ('ANNULE_USAGER', 'Annulé par usager'),
        ('REPORT_USAGER', 'Reporté par usager'),
        ('ANNULE_MDS', 'Annulé par MDS'),
        ('REPORT_MDS', 'Reporté par MDS'),
        ('ABSENT', 'Absent'),
    ]

    # TEMPS
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    duree_minutes = models.PositiveIntegerField(default=30)

    # RESSOURCES
    salle = models.ForeignKey('mds.MDSReception', on_delete=models.CASCADE, related_name='creneaux')
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='creneaux')
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.SET_NULL, null=True, blank=True, related_name='rdvs')
    

    # MÉTIER
    type_rdv = models.CharField(max_length=20, choices=TYPE_RDV_CHOICES, default='PERMANENCE')
    statut = models.CharField(max_length=20, choices=STATUT_RDV_CHOICES, default='DISPONIBLE')
    description = models.TextField(blank=True)
    notes_internes = models.TextField(blank=True)
    priorite = models.CharField(max_length=20, choices=[('NORMAL', 'Normal'), ('URGENT', 'Urgent'), ('TRES_URGENT', 'Très urgent')], default='NORMAL')

    # AUDIT
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='creneaux_crees')
    date_reservation = models.DateTimeField(null=True, blank=True)
    reserve_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='creneaux_reserves')

    class Meta:
        ordering = ['date', 'heure_debut']
        indexes = [
            models.Index(fields=['date', 'salle']),
            models.Index(fields=['statut', 'date']),
            models.Index(fields=['agent', 'date']),
            models.Index(fields=['beneficiaire', 'date']),
        ]

    def __str__(self):
        return f"{self.date} {self.heure_debut}-{self.heure_fin}"

    # --- DROITS ---
    def peut_etre_vu_par(self, user):
        if not user.is_authenticated: return False
        if user.is_superuser or user.a_la_capacite('peut_administrer'): return True
        if user == self.agent or user == self.cree_par: return True
        if self.salle and self.salle.mds:
            return UserMDSProfile.objects.filter(user=user, mds=self.salle.mds, actif=True).exists()
        return False

    def peut_etre_modifie_par(self, user):
        if not user.is_authenticated: return False
        if user.is_superuser or user.a_la_capacite('peut_administrer') or user.a_la_capacite('peut_valider'): return True
        if self.agent == user and self.statut not in {'VENU_RECU', 'VENU_NON_RECU', 'ABSENT'}: return True
        return False

    def peut_etre_reserve_par(self, user):
        if not user.is_authenticated or self.statut != 'DISPONIBLE': return False
        if user.is_superuser: return True
        if not user.a_la_capacite('peut_creer'): return False
        if self.salle and self.salle.mds:
            return UserMDSProfile.objects.filter(user=user, mds=self.salle.mds, actif=True).exists()
        return False

    # --- VALIDATION (Règles V2 strictes) ---
    def clean(self):
        errors = {}
        if self.heure_debut and self.heure_fin:
            if self.heure_debut >= self.heure_fin:
                errors['heure_fin'] = "L'heure de fin doit être postérieure à l'heure de début."
            if self.heure_debut < time(9, 0):
                errors['heure_debut'] = "Le premier rendez-vous commence à 09h00."
            if self.heure_fin > time(17, 0):
                errors['heure_fin'] = "La MDS ferme à 17h00."
            if self.heure_debut > time(16, 30):
                errors['heure_debut'] = "Le dernier rendez-vous débute à 16h30."
        
        if self.date and self.date < timezone.now().date():
            errors['date'] = "La date ne peut pas être dans le passé."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.heure_debut and self.heure_fin:
            debut = self.heure_debut.hour * 60 + self.heure_debut.minute
            fin = self.heure_fin.hour * 60 + self.heure_fin.minute
            self.duree_minutes = max(0, fin - debut)
        super().save(*args, **kwargs)

    # --- MÉTIERS (Logique V2 sécurisée + V1) ---
    def is_disponible(self):
        """Vérifie la disponibilité (inclut Jours Bloqués V1)"""
        from planning.utils import est_jour_ferie # V1
        if est_jour_ferie(self.date):
            return False
        
        # Vérification des blocages (Restauration V1)
        if JourBloque.objects.filter(
            Q(date=self.date),
            Q(salle=self.salle) | Q(agent=self.agent) | Q(salle__isnull=True, agent__isnull=True)
        ).exists():
            return False

        return self.statut == 'DISPONIBLE'

    def est_passe(self): # Restauration V1
        maintenant = timezone.now()
        if self.date < maintenant.date(): return True
        if self.date == maintenant.date() and self.heure_fin < maintenant.time(): return True
        return False

    def get_duree_affichage(self): # Restauration V1
        heures = self.duree_minutes // 60
        minutes = self.duree_minutes % 60
        return f"{heures}h{minutes:02d}" if heures > 0 else f"{minutes}min"

    @transaction.atomic
    def reserver(self, user, beneficiaire, description=""):
        """Verrou SQL anti-double réservation (V2)"""
        creneau = CreneauRdv.objects.select_for_update().get(pk=self.pk)
        if not creneau.peut_etre_reserve_par(user):
            raise PermissionError("Réservation interdite.")
        if creneau.statut != 'DISPONIBLE':
            raise ValidationError("Créneau déjà réservé.")

        creneau.statut = 'RESERVE'
        creneau.beneficiaire = beneficiaire
        creneau.description = description
        creneau.reserve_par = user
        creneau.date_reservation = timezone.now()
        creneau.save()

        HistoriqueCreneau.objects.create(
            creneau=creneau, action='RESERVATION',
            utilisateur=user, commentaire="Réservation sécurisée"
        )
        return creneau

    @transaction.atomic
    def annuler(self, user, motif="", par_mds=False):
        if not self.peut_etre_modifie_par(user):
            raise PermissionError("Annulation interdite.")

        ancien_statut = self.statut
        self.statut = 'ANNULE_MDS' if par_mds else 'DISPONIBLE'
        self.beneficiaire = None
        self.reserve_par = None
        self.date_reservation = None
        self.save()

        HistoriqueCreneau.objects.create(
            creneau=self, action='ANNULATION',
            utilisateur=user, commentaire=f"{ancien_statut} → {self.statut} | {motif}"
        )


# =============================================================================
# MODÈLE JOUR BLOQUÉ (Restauration V1 complète)
# =============================================================================

class JourBloque(models.Model):
    RAISON_CHOICES = [
        ('FERIE', 'Jour férié'),
        ('FORMATION', 'Formation'),
        ('ABSENCE', 'Absence collective'),
        ('MAINTENANCE', 'Maintenance'),
        ('CONGE', 'Congé'),
        ('AUTRE', 'Autre'),
    ]
    
    date = models.DateField()
    raison = models.CharField(max_length=20, choices=RAISON_CHOICES)
    raison_detail = models.TextField(blank=True)
    salle = models.ForeignKey('mds.MDSReception', on_delete=models.SET_NULL, null=True, blank=True)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    heure_debut = models.TimeField(default=time(0, 0))
    heure_fin = models.TimeField(default=time(23, 59))
    
    class Meta:
        ordering = ['date']
        unique_together = ['date', 'salle', 'agent']

    def __str__(self):
        return f"{self.date} - {self.get_raison_display()}"


# =============================================================================
# MODÈLE HISTORIQUE (Version V2)
# =============================================================================

class HistoriqueCreneau(models.Model):
    ACTIONS = [
        ('CREATION', 'Création'),
        ('MODIFICATION', 'Modification'),
        ('RESERVATION', 'Réservation'),
        ('ANNULATION', 'Annulation'),
    ]

    creneau = models.ForeignKey(CreneauRdv, on_delete=models.CASCADE, related_name='historique')
    action = models.CharField(max_length=20, choices=ACTIONS)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    date_action = models.DateTimeField(auto_now_add=True)
    commentaire = models.TextField(blank=True)
    anciennes_valeurs = models.JSONField(default=dict, blank=True)
    nouvelles_valeurs = models.JSONField(default=dict, blank=True)


    class Meta:
        ordering = ['-date_action']

class PermanenceExterne(models.Model):
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    salle = models.ForeignKey('mds.MDSReception', on_delete=models.CASCADE)
    jour_semaine = models.IntegerField(choices=HoraireMDS.JOURS_SEMAINE)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    
    recurrence = models.CharField(
        max_length=20,
        choices=[('HEBDO', 'Hebdomadaire'), ('MENSUEL', 'Mensuel (même semaine)')],
        default='HEBDO'
    )
    actif = models.BooleanField(default=True)
    date_debut = models.DateField(default=timezone.now)
    date_fin = models.DateField(null=True, blank=True)
    
    # Audit
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
