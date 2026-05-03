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
    matricule = models.CharField(max_length=15, unique=True, null=False, blank=False)
    
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
    
    service_principal = models.ForeignKey(
        'core.Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents_principaux',
        verbose_name="Service principal"
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

    def get_capacites_codes(self):
        """
        Retourne un ensemble (set) des codes de capacités de l'utilisateur.
        Méthode unique source de vérité pour les capacités.
        """
        if self.is_superuser:
            return set() # Superuser géré séparément
        
        return set(
            self.profils
            .filter(actif=True)
            .values_list("capacites__code", flat=True)
        )

    @property
    def capacites(self):
        """
        Renvoie un objet dynamique permettant d'accéder aux capacités via attributs.
        Usage : user.capacites.peut_creer → True/False
        """
        if self.is_superuser:
            # Superuser : toutes les capacités = True
            class AllRights:
                def __getattr__(self, name):
                    return True
                def __bool__(self):
                    return True
            return AllRights()
        
        # Récupération des codes de capacités via la méthode unique
        codes = self.get_capacites_codes()
        
        # Création d'une classe avec __getattr__
        class UserCapacites:
            def __init__(self, capacites_set):
                self._capacites = capacites_set
            
            def __getattr__(self, name):
                # Permet d'accéder à user.capacites.peut_creer
                return name in self._capacites
            
            def __bool__(self):
                # Permet de faire if user.capacites: ...
                return bool(self._capacites)
            
            def __contains__(self, item):
                # Permet de faire 'peut_creer' in user.capacites
                return item in self._capacites
            
            def __iter__(self):
                # Permet de faire for cap in user.capacites: ...
                return iter(self._capacites)
        
        return UserCapacites(codes)

    def a_acces_mds(self, mds):
        """
        Vérifie si l'utilisateur a un profil actif dans la MDS donnée.
        """
        if self.is_superuser:
            return True
        if not mds:
            return False
        
        # Vérifier via UserMDSProfile (la table de liaison MDS ↔ User)
        from mds.models import UserMDSProfile
        return UserMDSProfile.objects.filter(
            user=self, 
            mds=mds, 
            actif=True
        ).exists()

    def peut_agir_sur_objet(self, objet, capacite_requise=None):
        """Logique de sécurité croisée : Capacité métier + Barrière territoriale."""
        if self.is_superuser:
            return True

        if capacite_requise and not self.a_la_capacite(capacite_requise):
            return False

        mds_objet = getattr(objet, 'mds', None)
        if mds_objet is not None:
            return self.a_acces_mds(mds_objet)
    
        return True  # Pas de barrière territoriale si pas de MDS

    # ----------------------------------------------------------------------
    # MÉTHODES UTILITAIRES
    # ----------------------------------------------------------------------

    @property
    def est_cadre(self):
        """Alias : vérifie si l'utilisateur peut valider"""
        return self.a_la_capacite('peut_valider')

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        # Vérification de unicité du matricule avant sauvegarde
        if not self.pk and self.matricule:
            if User.objects.filter(matricule=self.matricule).exists():
                raise ValueError(f"Le matricule '{self.matricule}' existe déjà.")
        super().save(*args, **kwargs)

    def __str__(self):
        nom_complet = f"{self.last_name} {self.first_name}".strip()
        return f"{nom_complet} ({self.username})" if nom_complet else self.username
        
    # ------------------------------------------------------------------
    # CAPACITÉS — API UNIQUE
    # ------------------------------------------------------------------

    def a_la_capacite(self, code):
        """Vérifie si l'utilisateur possède une capacité donnée"""
        if self.is_superuser:
            return True
        return code in self.get_capacites_codes()

    # ------------------------------------------------------------------
    # COMPATIBILITÉ (TEMPORAIRE - À supprimer après migration)
    # ------------------------------------------------------------------

    def a_profil(self, code):
        """DEPRECATED : Utilisez a_la_capacite() à la place"""
        return self.profils.filter(code=code, actif=True).exists()
