# beneficiaire/models.py
"""
Modèles pour l'application bénéficiaire - VERSION RÉSEAU FAMILIAL & CORE
FICHIER 100% CORRIGÉ - Sécurité via a_la_capacite() et UserMDSProfile
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import random
import string
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db.models import Q

class Beneficiaire(models.Model):
    STATUT_CHOICES = [
        ('ACTIF', 'Actif'),
        ('INACTIF', 'Inactif'),
        ('SORTI', 'Sorti'),
        ('DECEDE', 'Décédé'),
        ('ARCHIVE', 'Archivé'),
    ]

    MOTIF_SORTIE_CHOICES = [
        ('SEPARATION', 'Séparation'),
        ('DIVORCE', 'Divorce'),
        ('DECES', 'Décès'),
        ('DEMENAGEMENT', 'Déménagement'),
        ('PLACEMENT', 'Placement'),
        ('MAJORITE', 'Majorité'),
        ('FIN_DROITS', 'Fin de droits'),
        ('AUTRE', 'Autre'),
    ]

    # Identification
    code_interne = models.CharField(max_length=20, unique=True, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='ACTIF')
    
    marital_status = models.CharField(
        max_length=50,
        choices=[
            ('CELIBATAIRE', 'Célibataire'),
            ('MARIE', 'Marié(e)'),
            ('PACSE', 'Pacsé(e)'),
            ('CONCUBINAGE', 'En concubinage'),
            ('DIVORCE', 'Divorcé(e)'),
            ('VEUF', 'Veuf/Veuve'),
            ('SEPARE', 'Séparé(e)'),
        ],
        blank=True, null=True, verbose_name="Situation familiale"
    )

    # État civil
    civilite = models.CharField(max_length=5, choices=[('M.', 'M.'), ('MME', 'Mme')])
    nom = models.CharField(max_length=30)
    prenom = models.CharField(max_length=30)
    nom_naissance = models.CharField(max_length=30, blank=True)
    date_naissance = models.DateField()
    lieu_naissance = models.CharField(max_length=50, blank=True)
    
    # Situation personnelle / sociale (PDF AFASE)
    
    SITUATION_CHOICES = [
        ('SCOLARISE', 'Scolarisé'),
        ('ETUDIANT', 'Étudiant'),
        ('ACTIF', 'En activité'),
        ('CHOMAGE', 'Sans emploi / chômage'),
        ('RSA', 'Bénéficiaire RSA'),
        ('HANDICAP', 'Situation de handicap'),
        ('SANS_ACTIVITE', 'Sans activité'),
    ]

    situation = models.CharField(
        max_length=25,
        choices=SITUATION_CHOICES,
        blank=True,
        verbose_name="Situation actuelle"
    )

    # Administratif
    nir = models.CharField(max_length=15, blank=True)
    numero_caf = models.CharField(max_length=10, blank=True)
    numero_france_travail = models.CharField(max_length=20, blank=True, null=True)
    numero_fiscal = models.CharField(max_length=20, blank=True, null=True)
    numero_genesis = models.CharField(max_length=50, blank=True, null=True, verbose_name="Numéro GENESIS", help_text="Numéro d'identification externe (GENESIS)")

    # Contact
    adresse = models.TextField()
    code_postal = models.CharField(max_length=5)
    ville = models.CharField(max_length=100)
    telephone_mobile = models.CharField(max_length=20, blank=True)
    telephone_fixe = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    # Rattachement structurel
    mds = models.ForeignKey('mds.MDS', on_delete=models.SET_NULL, null=True, related_name='beneficiaires')
    referent_mds = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='beneficiaires_suivis')

    # Sortie et décès
    date_entree = models.DateField(null=True, blank=True)
    date_sortie = models.DateField(null=True, blank=True)
    motif_sortie = models.CharField(max_length=50, choices=MOTIF_SORTIE_CHOICES, null=True, blank=True)
    detail_sortie = models.TextField(blank=True, null=True)
    est_decede = models.BooleanField(default=False)
    date_deces = models.DateField(null=True, blank=True)

    # Tracking
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='beneficiaires_crees')




    class Meta:
        verbose_name = "Bénéficiaire"
        ordering = ['nom', 'prenom']
        indexes = [
            models.Index(fields=['nom', 'prenom']),
            models.Index(fields=['code_interne']),
        ]

    def __str__(self):
        return f"{self.nom.upper()} {self.prenom} ({self.code_interne})"

    @property
    def documents_ged(self):
        """Tous les documents GED de ce bénéficiaire"""
        from ged.models import DocumentGED
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(self)
        return DocumentGED.objects.filter(
            content_type=ct, object_id=self.id
        ).distinct()
    
    @property    
    def liens_familiaux(self):
        """Tous les liens (initiés ou reçus) de ce bénéficiaire"""
        return LienFamilial.objects.filter(
            Q(personne_a=self) | Q(personne_b=self)
        ).select_related('personne_a', 'personne_b')
        
    @property
    def enfants(self):
        """Retourne les bénéficiaires liés comme 'ENFANT' via les liens familiaux."""
        from beneficiaire.models import LienFamilial, Beneficiaire
        liens = LienFamilial.objects.filter(
            type_lien="ENFANT"
        ).filter(
            models.Q(personne_a=self) | models.Q(personne_b=self)
        )

        ids = []
        for lien in liens:
            if lien.personne_a_id != self.id:
                ids.append(lien.personne_a_id)
            if lien.personne_b_id != self.id:
                ids.append(lien.personne_b_id)

        return Beneficiaire.objects.filter(id__in=ids)


    def peut_etre_vu_par(self, user):
        """✅ CORRIGÉ CORE : Utilise UserMDSProfile + a_la_capacite"""
        if user.is_superuser or user.a_la_capacite('peut_voir_stats'):
            return True
        
        # Vérification via profil MDS actif
        if self.mds:
            try:
                from mds.models import UserMDSProfile
                profile = UserMDSProfile.objects.filter(
                    user=user, 
                    mds=self.mds, 
                    actif=True
                ).first()
                return bool(profile)
            except:
                pass
        
        # Fallback : accès via liens familiaux (si capacité)
        if user.a_la_capacite('peut_creer'):
            liens = LienFamilial.objects.filter(
                Q(personne_a=self, personne_b__mds__usermdsprofile__user=user) |
                Q(personne_b=self, personne_a__mds__usermdsprofile__user=user)
            )
            return liens.exists()
        
        return False

    def peut_etre_modifie_par(self, user):
        """✅ CORRIGÉ CORE : peut_creer + même MDS"""
        if user.is_superuser or user.a_la_capacite('peut_administrer'):
            return True
        return (user.a_la_capacite('peut_creer') and self.peut_etre_vu_par(user))

class LienFamilial(models.Model):
    TYPE_LIEN_CHOICES = [
        ('PARENT', 'Parent (Père/Mère)'),
        ('ENFANT', 'Enfant'),
        ('CONJOINT', 'Conjoint / Concubin'),
        ('PLACEMENT', 'Famille d\'accueil / Placement'),
        ('TUTEUR', 'Tuteur / Curateur'),
        ('TIERS', 'Tiers de confiance'),
        ('AUTRE', 'Autre lien'),
    ]

    personne_a = models.ForeignKey(
        Beneficiaire, 
        on_delete=models.CASCADE, 
        related_name='liens_inities',
        blank=True, null=True
    )
    personne_b = models.ForeignKey(
        Beneficiaire, 
        on_delete=models.CASCADE, 
        related_name='liens_recus',
        blank=True, null=True
    )
    
    type_lien = models.CharField(max_length=20, choices=TYPE_LIEN_CHOICES)
    vit_au_foyer = models.BooleanField(default=True, help_text="L'individu réside-t-il physiquement avec cette personne ?")
    est_responsable_legal = models.BooleanField(default=False)
    
    date_debut = models.DateField(default=timezone.now)
    date_fin = models.DateField(null=True, blank=True)
    commentaire = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Lien familial"
        verbose_name_plural = "Liens familiaux"
        unique_together = ('personne_a', 'personne_b', 'type_lien')
        indexes = [models.Index(fields=['personne_a', 'personne_b'])]

    def __str__(self):
        return f"{self.personne_a} ↔ {self.personne_b} ({self.get_type_lien_display()})"

class DocumentBeneficiaireLink(models.Model):
    TYPE_DOCUMENT_CHOICES = [
        ('IDENTITE', "Pièce d'identité"),
        ('DOMICILIATION', 'Justificatif de domicile'),
        ('RESSOURCES', 'Justificatif de ressources'),
        ('AUTRE', 'Autre document'),
    ]

    beneficiaire = models.ForeignKey(Beneficiaire, on_delete=models.CASCADE, related_name='documents')
    document_ged = models.ForeignKey('ged.DocumentGED', on_delete=models.CASCADE)
    type_document = models.CharField(max_length=50, choices=TYPE_DOCUMENT_CHOICES)
    date_creation = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    valide = models.BooleanField(default=False)

@property
def enfants(self):
    from beneficiaire.models import LienFamilial
    return LienFamilial.objects.filter(
        type_lien="ENFANT"
    ).filter(
        models.Q(personne_b=self) | models.Q(personne_a=self)
    )

@receiver(pre_save, sender=Beneficiaire)
def generate_code_interne(sender, instance, **kwargs):
    if not instance.code_interne:
        prefix = "BEN"
        for _ in range(10):
            random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            code = f"{prefix}-{random_str}"
            if not Beneficiaire.objects.filter(code_interne=code).exists():
                instance.code_interne = code
                break
