# mds/models.py version core user compatible

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from core.mixins import AuditedMixin, TimestampedMixin
from datetime import time

User = get_user_model()

# ==========================================================================
# 1. MODÈLE MDS (Territoire)
# ==========================================================================

class MDS(AuditedMixin):
    """
    Maison Départementale de la Solidarité.
    Point d'ancrage territorial pour la sécurité et les bénéficiaires.
    """

    code_mds = models.CharField(
        max_length=10,
        unique=True,
        help_text="Ex: MDS01, MDS02"
    )
    nom = models.CharField(max_length=200)

    # Localisation
    adresse = models.TextField()
    code_postal = models.CharField(max_length=10)
    ville = models.CharField(max_length=100)
    departement = models.CharField(max_length=100, default="Morbihan")

    # Contact
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    site_web = models.URLField(blank=True)

    # Gestion
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mdss_dirigees',
        help_text="L'utilisateur doit posséder la capacité de validation/encadrement."
    )

    # Statut
    active = models.BooleanField(default=True)
    date_ouverture = models.DateField(null=True, blank=True)
    date_fermeture = models.DateField(null=True, blank=True)

    # Capacité RH
    nb_agents_max = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(500)]
    )

    # Coordonnées & Secteur
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    communes = models.JSONField(default=list, blank=True, help_text="Liste des codes INSEE")
    
    services_proposes = models.JSONField(default=list, blank=True)
    configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['code_mds']
        indexes = [
            models.Index(fields=['code_mds']),
            models.Index(fields=['ville', 'active']),
        ]

    def __str__(self):
        return f"{self.code_mds} - {self.nom} ({self.ville})"

    # ----------------------------------------------------------------------
    # LOGIQUE UTILISATEURS (Branchée sur CAPACITÉS)
    # ----------------------------------------------------------------------

    def get_utilisateurs_par_capacite(self, nom_capacite):
        """
        Cherche les utilisateurs actifs de cette MDS possédant une capacité précise.
        CORRECTION : Utilisation d'un dictionnaire de filtre dynamique pour éviter la SyntaxError.
        """
        # 1. On récupère les IDs des agents liés à cette MDS via UserMDSProfile
        ids_utilisateurs = UserMDSProfile.objects.filter(
            mds=self, actif=True
        ).values_list('user_id', flat=True)

        # 2. Construction dynamique du filtre pour le profil CORE
        # Exemple : si nom_capacite='peut_valider', filtre sera {'profils__peut_valider': True}
        filtre_capacite = {f"profils__{nom_capacite}": True}

        # 3. On filtre le modèle User
        return User.objects.filter(
            id__in=ids_utilisateurs,
            is_active=True,
            **filtre_capacite
        ).distinct()

    def get_utilisateurs_actifs(self):
        """Retourne tous les utilisateurs liés à cette MDS (actifs en système et en profil)."""
        ids_utilisateurs = UserMDSProfile.objects.filter(
            mds=self, actif=True
        ).values_list('user_id', flat=True)
        return User.objects.filter(id__in=ids_utilisateurs, is_active=True)

    # ----------------------------------------------------------------------
    # ACTIONS RH
    # ----------------------------------------------------------------------

    def ajouter_utilisateur(self, user, principale=False, peut_gerer=False):
        """Inscrit un utilisateur dans la MDS."""
        profile, created = UserMDSProfile.objects.update_or_create(
            user=user,
            mds=self,
            defaults={
                'principale': principale,
                'peut_gerer_utilisateurs': peut_gerer,
                'actif': True
            }
        )
        return profile

    def retirer_utilisateur(self, user):
        """Désactive le lien entre un utilisateur et la MDS (pas de suppression physique)."""
        return UserMDSProfile.objects.filter(user=user, mds=self).update(actif=False)

    # ----------------------------------------------------------------------
    # MÉTHODES MÉTIER & DISPO
    # ----------------------------------------------------------------------

    def est_ouverte(self):
        """Vérifie l'ouverture selon l'heure locale."""
        maintenant = timezone.localtime()
        jour_actuel = maintenant.weekday()
        horaire = self.horaires.filter(jour=jour_actuel).first()
        if not horaire:
            return False
        return horaire.heure_ouverture <= maintenant.time() <= horaire.heure_fermeture

    def get_capacite_actuelle(self):
        return UserMDSProfile.objects.filter(mds=self, actif=True).count()

    def get_pourcentage_occupation(self):
        if self.nb_agents_max > 0:
            return round((self.get_capacite_actuelle() / self.nb_agents_max) * 100, 1)
        return 0

    # ----------------------------------------------------------------------
    # SÉCURITÉ (Système Unifié)
    # ----------------------------------------------------------------------

    def peut_etre_vue_par(self, user):
        return user.is_authenticated

    def peut_etre_modifiee_par(self, user):
        """
        Une MDS ne peut être modifiée que par un superutilisateur 
        ou un cadre rattaché à CETTE MDS ayant le droit de gestion.
        """
        if user.is_superuser:
            return True
        return UserMDSProfile.objects.filter(
            user=user, mds=self, peut_gerer_utilisateurs=True, actif=True
        ).exists()

    @property
    def coordonnees_completes(self):
        return f"{self.adresse}, {self.code_postal} {self.ville}"


# ==========================================================================
# 2. MODÈLE HORAIRES
# ==========================================================================

class HoraireMDS(TimestampedMixin):
    JOURS_SEMAINE = [(0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'), (3, 'Jeudi'), (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche')]

    mds = models.ForeignKey(MDS, on_delete=models.CASCADE, related_name='horaires')
    jour = models.IntegerField(choices=JOURS_SEMAINE)
    heure_ouverture = models.TimeField()
    heure_fermeture = models.TimeField()
    pause_debut = models.TimeField(null=True, blank=True)
    pause_fin = models.TimeField(null=True, blank=True)

    type_jour = models.CharField(
        max_length=20, 
        choices=[('NORMAL', 'Jour normal'), ('FERIE', 'Jour férié'), ('EXCEPTION', 'Exceptionnel')],
        default='NORMAL'
    )

    class Meta:
        ordering = ['mds', 'jour']
        unique_together = ['mds', 'jour']

    def __str__(self):
        return f"{self.mds.code_mds} - {self.get_jour_display()}"


# ==========================================================================
# 3. MODÈLE PROFIL UTILISATEUR MDS (Liaison Pivot)
# ==========================================================================

class UserMDSProfile(AuditedMixin):
    """
    Définit les droits territoriaux d'un utilisateur.
    C'est ici que l'on sait si un agent 'appartient' à une MDS.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profils_mds')
    mds = models.ForeignKey(MDS, on_delete=models.CASCADE, related_name='profils_utilisateurs')
    
    principale = models.BooleanField(default=False, help_text="MDS de rattachement par défaut")
    peut_gerer_utilisateurs = models.BooleanField(default=False, help_text="Droit d'administration locale (Cadre)")
    peut_voir_statistiques = models.BooleanField(default=False)
    
    actif = models.BooleanField(default=True)
    date_debut = models.DateField(default=timezone.now)
    date_fin = models.DateField(null=True, blank=True)
    
    role_specifique = models.CharField(max_length=100, blank=True, help_text="Ex: Référent RSA")
    bureau = models.CharField(max_length=50, blank=True)
    telephone_interne = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ['user', 'mds']
        indexes = [
            models.Index(fields=['user', 'actif']),
            models.Index(fields=['mds', 'actif']),
        ]

    def __str__(self):
        return f"{self.user.username} @ {self.mds.code_mds}"

    @property
    def est_actif(self):
        if not self.actif:
            return False
        if self.date_fin and self.date_fin < timezone.now().date():
            return False
        return True


# ==========================================================================
# 4. RÉCEPTION ET ACCUEIL
# ==========================================================================

class MDSReception(AuditedMixin):
    """
    Salle de réception d'une MDS.
    
    Les horaires définis ici (horaire_debut/horaire_fin) sont les HORAIRES GLOBAUX
    de disponibilité de la salle, indépendamment des plannings individuels des agents
    (gérés via DemiJourneeReception).
    """
    mds = models.ForeignKey(MDS, on_delete=models.CASCADE, related_name='salles_reception')
    nom = models.CharField(max_length=100)
    type_salle = models.CharField(max_length=20, default='BUREAU')
    capacite = models.PositiveIntegerField(default=1)
    actif = models.BooleanField(default=True)
    horaire_debut = models.TimeField(default='09:00')
    horaire_fin = models.TimeField(default='17:00')

# ✅ NOUVEAUX CHAMPS - Disponibilité par jour de la semaine
    disponible_lundi = models.BooleanField(
        default=True,
        verbose_name="Disponible le lundi",
        help_text="Cocher si la salle est ouverte le lundi"
    )
    disponible_mardi = models.BooleanField(
        default=True,
        verbose_name="Disponible le mardi"
    )
    disponible_mercredi = models.BooleanField(
        default=True,
        verbose_name="Disponible le mercredi"
    )
    disponible_jeudi = models.BooleanField(
        default=True,
        verbose_name="Disponible le jeudi"
    )
    disponible_vendredi = models.BooleanField(
        default=True,
        verbose_name="Disponible le vendredi"
    )
    disponible_samedi = models.BooleanField(
        default=False,
        verbose_name="Disponible le samedi"
    )
    disponible_dimanche = models.BooleanField(
        default=False,
        verbose_name="Disponible le dimanche"
    )

    def __str__(self):
        return f"{self.nom} ({self.mds.code_mds})"
    

class DemiJourneeReception(TimestampedMixin):
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demi_journees_reception')
    mds = models.ForeignKey(MDS, on_delete=models.CASCADE, related_name='demi_journees_reception')
    jour_semaine = models.IntegerField(choices=HoraireMDS.JOURS_SEMAINE)
    type_demi_journee = models.CharField(max_length=20, choices=[('MATIN', 'Matin'), ('APRES_MIDI', 'Après-midi')])
    actif = models.BooleanField(default=True)

    # ✅ On enlève les default ici, ils seront gérés dans save()
    heure_debut = models.TimeField(
        verbose_name="Heure de début",
        help_text="Heure de début de la demi-journée (ex: 9h pour le matin, 13h30 pour l'après-midi)"
    )
    heure_fin = models.TimeField(
        verbose_name="Heure de fin",
        help_text="Heure de fin de la demi-journée (ex: 12h pour le matin, 17h pour l'après-midi)"
    )
    
    class Meta:
        unique_together = ['agent', 'mds', 'jour_semaine', 'type_demi_journee']
        verbose_name = "Demi-journée de réception"
        verbose_name_plural = "Demi-journées de réception"
    
    def __str__(self):
        jour_nom = dict(HoraireMDS.JOURS_SEMAINE).get(self.jour_semaine, "Inconnu")
        periode = "Matin" if self.type_demi_journee == 'MATIN' else "Après-midi"
        return f"{self.agent.get_full_name()} - {jour_nom} {periode}"
    
    def save(self, *args, **kwargs):
        """Définir les horaires par défaut selon le type de demi-journée"""
        # Seulement si les horaires ne sont pas déjà définis
        if not self.heure_debut or not self.heure_fin:
            if self.type_demi_journee == 'MATIN':
                self.heure_debut = self.heure_debut or time(9, 0)
                self.heure_fin = self.heure_fin or time(12, 0)
            elif self.type_demi_journee == 'APRES_MIDI':
                self.heure_debut = self.heure_debut or time(13, 30)
                self.heure_fin = self.heure_fin or time(17, 0)
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validation des horaires"""
        from django.core.exceptions import ValidationError
        errors = {}
        
        if self.heure_debut >= self.heure_fin:
            errors['heure_fin'] = "L'heure de fin doit être après l'heure de début."
        
        # Validation cohérence matin/après-midi - stricte pour respecter la pause 12h-13h
        if self.type_demi_journee == 'MATIN' and self.heure_fin > time(12, 0):
            errors['heure_fin'] = "Une demi-journée 'Matin' ne peut pas se terminer après 12h (pause obligatoire)."
        
        if self.type_demi_journee == 'APRES_MIDI' and self.heure_debut < time(13, 0):
            errors['heure_debut'] = "Une demi-journée 'Après-midi' ne peut pas commencer avant 13h (pause obligatoire)."
        
        if errors:
            raise ValidationError(errors)


# ==========================================================================
# 5. SIGNAUX (Synchronisation MDS Principale)
# ==========================================================================

@receiver(post_save, sender=UserMDSProfile)
def sync_user_mds_principale(sender, instance, **kwargs):
    """Synchronise le champ mds_principale_id de l'utilisateur"""
    
    # 1. Un seul profil principal par utilisateur
    if instance.principale and instance.est_actif:
        UserMDSProfile.objects.filter(
            user=instance.user, principale=True
        ).exclude(pk=instance.pk).update(principale=False)
    
    # 2. Synchronisation du champ mds_principale_id
    if instance.principale and instance.actif and instance.est_actif:
        # Si ce profil est principal ET actif → on affecte cette MDS
        instance.user.mds_principale_id = instance.mds_id
        instance.user.save(update_fields=['mds_principale_id'])
    else:
        # Si ce profil n'est plus principal ou inactif
        # On retire la MDS principale SEULEMENT si c'était celle-ci
        if instance.user.mds_principale_id == instance.mds_id:
            # Cherche si l'utilisateur a un AUTRE profil principal actif
            autre_profil_principal = UserMDSProfile.objects.filter(
                user=instance.user,
                principale=True,
                actif=True
            ).exclude(pk=instance.pk).first()
            
            if autre_profil_principal:
                # Si oui, on bascule vers cet autre profil
                instance.user.mds_principale_id = autre_profil_principal.mds_id
            else:
                # Sinon, on met à NULL
                instance.user.mds_principale_id = None
            
            instance.user.save(update_fields=['mds_principale_id'])

@receiver(pre_delete, sender=UserMDSProfile)
def clean_user_mds_on_delete(sender, instance, **kwargs):
    """Nettoyage lors de la suppression d'un profil MDS"""
    if instance.user.mds_principale_id == instance.mds_id:
        # On retire la MDS principale
        instance.user.mds_principale_id = None
        instance.user.save(update_fields=['mds_principale_id'])

@receiver(post_save, sender=MDS)
def sync_responsable_mds(sender, instance, **kwargs):
    """Synchronise automatiquement le responsable avec UserMDSProfile"""
    if instance.responsable:
        UserMDSProfile.objects.update_or_create(
            user=instance.responsable,
            mds=instance,
            defaults={
                'peut_gerer_utilisateurs': True,
                'actif': True,
                'principale': False  # ou True si vous voulez
            }
        )
# ==========================================================================
# 6. SIGNAL AUTO-CADRE : peut_gerer_utilisateurs automatique pour les cadres
# ==========================================================================

@receiver(post_save, sender=UserMDSProfile)
def auto_cadre_peut_gerer(sender, instance, **kwargs):
    """
    Auto-attribution : si l'agent est cadre, il peut automatiquement 
    gérer les utilisateurs et voir les statistiques.
    S'exécute à la création ET à chaque modification du profil MDS.
    """
    # Vérifier si l'utilisateur a le profil cadre (id=3)
    est_cadre = instance.user.profils.filter(id=3).exists()
    
    if est_cadre:
        # Mise à jour directe en base pour éviter les boucles infinies
        UserMDSProfile.objects.filter(pk=instance.pk).update(
            peut_gerer_utilisateurs=True,
            peut_voir_statistiques=True
        )
    # Optionnel : retirer les droits si l'utilisateur n'est plus cadre
    # (décommente si besoin)
    # else:
    #     UserMDSProfile.objects.filter(pk=instance.pk).update(
    #         peut_gerer_utilisateurs=False,
    #         peut_voir_statistiques=False
    #     )
