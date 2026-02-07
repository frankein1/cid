# core/models/user.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta
from core.mixins import TimestampedMixin

# ==========================================================================
# 1. CUSTOM MANAGER
# ==========================================================================

class CustomUserManager(BaseUserManager):
    """
    Manager personnalisé pour le modèle User.
    """
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError('Le nom d\'utilisateur est obligatoire')
        
        email = self.normalize_email(email) if email else ''
        
        # Valeurs par défaut pour les champs obligatoires
        extra_fields.setdefault('telephone_professionnel', '')
        extra_fields.setdefault('telephone_mobile', '')
        extra_fields.setdefault('email_professionnel', email)
        extra_fields.setdefault('ldap_dn', '')
        extra_fields.setdefault('force_change_password', False)
        extra_fields.setdefault('double_authentification_active', False)
        extra_fields.setdefault('preferences', {})
        extra_fields.setdefault('est_remplacant', False)
        
        user = self.model(username=username, email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superutilisateur doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superutilisateur doit avoir is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)

# ==========================================================================
# 2. MODÈLE USER (Centralisé pour CID)
# ==========================================================================

class User(TimestampedMixin, AbstractUser):
    """
    Utilisateur système - Extension de AbstractUser.
    Intègre la logique de droits croisés : Profil Métier + Territoire (MDS).
    """
    objects = CustomUserManager()
    
    # Identifiants
    matricule = models.CharField(max_length=20, unique=True, null=False, blank=False)
    
    # Coordonnées
    telephone_professionnel = models.CharField(max_length=20, blank=True, default='')
    telephone_mobile = models.CharField(max_length=20, blank=True, default='')
    email_professionnel = models.EmailField(blank=True, default='')
    
    # Statut RH
    est_remplacant = models.BooleanField(default=False)
    numero_interne = models.CharField(max_length=20, blank=True, default='')
    date_arrivee = models.DateField(null=True, blank=True)
    date_depart = models.DateField(null=True, blank=True)
    
    # Sécurité et Authentification
    date_dernier_changement_mdp = models.DateField(null=True, blank=True)
    date_expiration_mdp = models.DateField(null=True, blank=True)
    ldap_dn = models.CharField(max_length=255, blank=True, default='')
    force_change_password = models.BooleanField(default=False)
    double_authentification_active = models.BooleanField(default=False)
    
    # Préférences et Signature
    preferences = models.JSONField(default=dict, blank=True)
    signature_manuscrite = models.CharField(max_length=100, blank=True, default='')
    
    # Structure et Rattachement
    services_secondaires = models.ManyToManyField(
        'core.Service',
        related_name='agents_secondaires',
        blank=True,
    )
    
    mds_principale = models.ForeignKey(
        'mds.MDS',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utilisateurs_principaux',
    )
    
    # Profils CID (Lien vers les capacités métier)
    profils = models.ManyToManyField(
        'core.Profil',
        related_name='utilisateurs',
        blank=True,
    )
    
    # Audit
    derniere_connexion_ip = models.GenericIPAddressField(null=True, blank=True)
    nombre_connexions = models.PositiveIntegerField(default=0)
    cree_par = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='utilisateurs_crees'
    )
    modifie_par = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='utilisateurs_modifies'
    )
    
    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['matricule']),
            models.Index(fields=['email']),
        ]

    # ----------------------------------------------------------------------
    # SYSTÈME DE DROITS UNIFIÉ (MÉTIER + MDS)
    # ----------------------------------------------------------------------

    def a_la_capacite(self, nom_capacite):
        """Vérifie si l'utilisateur possède une compétence métier via ses profils."""
        if self.is_superuser:
            return True
        # --- LOGIQUE GÉNÉRIQUE (Alias) ---
        # Si on demande 'peut_voir', on vérifie si l'utilisateur a au moins 
        # le droit d'instruire (Agent) ou de valider (Cadre).
        if nom_capacite == 'peut_voir':
            return self.profils.filter(
                models.Q(peut_instruire=True) | models.Q(peut_valider=True)
            ).exists()

        # --- LOGIQUE PAR DÉFAUT (Champs réels du modèle Profil) ---
        return self.profils.filter(**{nom_capacite: True}).exists()
        
        

    @property
    def capacites(self):
        """
        Permet l'accès aux capacités dans les templates HTML.
        Usage : {% if user.capacites.peut_creer %}
        """
        if self.is_superuser:
            # Pour les superusers, on renvoie un objet qui répond toujours True
            class SuperUserRights:
                def __getattr__(self, name): return True
            return SuperUserRights()
        
        # On renvoie le premier profil trouvé pour cet utilisateur
        return self.profils.first()

    def a_acces_mds(self, mds):
        """
        Vérifie si l'utilisateur a un profil actif dans la MDS donnée.
        """
        if self.is_superuser:
            return True
        if not mds:
            return False
        return (self.mds_principale == mds or 
            self.services_secondaires.filter(mds=mds).exists())

    def peut_agir_sur_objet(self, objet, capacite_requise=None):
        """Logique de sécurité croisée : Capacité métier + Barrière territoriale."""
        if self.is_superuser:
            return True

        if capacite_requise and not self.a_la_capacite(capacite_requise):
            return False

        mds_objet = getattr(objet, 'mds', None)
        if mds_objet:
            return self.a_acces_mds(mds_objet)
            
        return True


    # ----------------------------------------------------------------------
    # MÉTHODES UTILITAIRES
    # ----------------------------------------------------------------------

    @property
    def est_cadre(self):
        # Mis à jour avec le nouveau nom de champ simplifié
        return self.a_la_capacite('peut_valider')

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        nom_complet = f"{self.last_name} {self.first_name}".strip()
        return f"{nom_complet} ({self.username})" if nom_complet else self.username
