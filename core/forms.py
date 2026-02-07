# /srv/django/si-ditas/core/forms.py - VERSION CORRIGÉE COMPLÈTE ET SÉCURISÉE

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

# Obtenir le modèle User personnalisé
User = get_user_model()

# Import des modèles nécessaires (avec gestion des erreurs si l'app n'est pas installée)
try:
    from mds.models import MDS
except ImportError:
    MDS = None

try:
    from .models import Service
except ImportError:
    Service = None

# Regex pour les numéros de téléphone français
FRENCH_PHONE_REGEX = r'^(\+33|0)[1-9]([ .]?[0-9]{2}){4}$'


# =======================================================
# FORMULAIRES D'AUTHENTIFICATION (Pour l'Admin)
# =======================================================

class CustomUserCreationForm(UserCreationForm):
    """Formulaire de création d'utilisateur pour Django Admin."""
    
    telephone_professionnel = forms.CharField(
        max_length=20,
        required=False,
        validators=[RegexValidator(FRENCH_PHONE_REGEX)],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '01 23 45 67 89'
        }),
        help_text="Format : 01 23 45 67 89 ou +33123456789"
    )
    
    telephone_mobile = forms.CharField(
        max_length=20,
        required=False,
        validators=[RegexValidator(FRENCH_PHONE_REGEX)],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '06 12 34 56 78'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'prenom.nom@departement.fr'
        }),
        help_text="Email professionnel"
    )
    
    class Meta:
        model = User
        # La liste est explicite et ne contient pas 'service_principal'
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'matricule', 'telephone_professionnel', 'telephone_mobile',
            'mds_principale', 'is_active'
            # Note: service_principal retiré temporairement
        )
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'matricule': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mds_principale': forms.Select(attrs={'class': 'form-control'}),
        }
        
    def clean_telephone_professionnel(self):
        """Validation du téléphone professionnel"""
        tel = self.cleaned_data.get('telephone_professionnel')
        if tel and not tel.startswith(('0', '+33')):
            raise forms.ValidationError(
                "Numéro de téléphone invalide. Format attendu : 01 23 45 67 89 ou +33123456789"
            )
        return tel

    def clean_telephone_mobile(self):
        """Validation du téléphone mobile"""
        tel = self.cleaned_data.get('telephone_mobile')
        if tel and not tel.startswith(('0', '+33')):
            raise forms.ValidationError(
                "Numéro de téléphone invalide. Format attendu : 06 12 34 56 78 ou +33612345678"
            )
        return tel
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personnalisation des widgets
        if 'mds_principale' in self.fields:
            self.fields['mds_principale'].widget.attrs.update({'class': 'form-control'})


class CustomUserChangeForm(UserChangeForm):
    """Formulaire de modification d'utilisateur pour Django Admin."""
    
    class Meta:
        model = User
        # --- CORRECTION DU FieldError : On liste explicitement les champs au lieu de '__all__' ---
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'matricule', 'telephone_professionnel', 'telephone_mobile',
            'mds_principale', 'is_active',
            # Champs de statut et permissions pour l'admin :
            'is_staff', 'is_superuser', 'groups', 'user_permissions', 
            # Les champs 'password' et 'last_login' sont gérés par la base UserChangeForm
        )
        # --------------------------------------------------------------------------------------
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'matricule': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telephone_professionnel': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone_mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'mds_principale': forms.Select(attrs={'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ce bloc de suppression n'est plus strictement nécessaire avec le Meta.fields explicite
        # mais on le laisse pour la rétrocompatibilité ou d'autres cas
        if 'service_principal' in self.fields:
            self.fields.pop('service_principal')
        
        # Personnalisation des widgets pour mds_principale
        if 'mds_principale' in self.fields:
            self.fields['mds_principale'].widget.attrs.update({'class': 'form-control'})
        
        # Retirer le champ 'password' de l'admin change form (car on le gère à part)
        if 'password' in self.fields:
            self.fields.pop('password')


# =======================================================
# FORMULAIRES DE VUES (Pour mon_profil, export, etc.)
# =======================================================

class UserProfileForm(forms.ModelForm):
    """Formulaire de profil utilisateur pour l'auto-édition."""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'telephone_professionnel', 'telephone_mobile']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nom'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'email@departement.fr'
            }),
            'telephone_professionnel': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '01 23 45 67 89'
            }),
            'telephone_mobile': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '06 12 34 56 78'
            }),
        }


class PersonnelSearchForm(forms.Form):
    """Formulaire de recherche de personnel."""
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom, prénom, matricule, email...',
            'autocomplete': 'off'
        }),
        label="Recherche"
    )
    
    service = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Service",
        empty_label="Tous les services"
    )
    
    mds = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="MDS principale",
        empty_label="Toutes les MDS"
    )
    
    statut = forms.ChoiceField(
        choices=[
            ('', 'Tous les statuts'),
            ('actif', 'Actifs seulement'),
            ('inactif', 'Inactifs seulement'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Statut"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialiser les querysets dynamiquement
        try:
            from .models import Service
            self.fields['service'].queryset = Service.objects.all().order_by('nom')
        except ImportError:
            self.fields['service'].queryset = User.objects.none()
        
        try:
            from mds.models import MDS
            self.fields['mds'].queryset = MDS.objects.all().order_by('nom')
        except ImportError:
            self.fields['mds'].queryset = User.objects.none()


class ExportPersonnelForm(forms.Form):
    """Formulaire pour l'export du personnel."""
    
    INFORMATIONS_CHOICES = [
        ('nom_complet', 'Nom complet'),
        ('matricule', 'Matricule (badge)'),
        ('email', 'Email professionnel'),
        ('telephone_professionnel', 'Téléphone professionnel'),
        ('telephone_mobile', 'Téléphone mobile'),
        # ('service_principal', 'Service principal'),  # Retiré temporairement
        ('mds_principale', 'MDS principale'),
        ('profils', 'Profils métiers'),
        ('date_arrivee', 'Date d\'arrivée'),
        ('est_actif', 'Statut actif'),
    ]
    
    informations = forms.MultipleChoiceField(
        choices=INFORMATIONS_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        initial=['nom_complet', 'matricule', 'email', 'telephone_professionnel'],
        label="Informations à inclure",
        help_text="Sélectionnez les informations à exporter"
    )
    
    utilisateurs = forms.ModelMultipleChoiceField(
        # --- CORRECTION DU RuntimeWarning : queryset=None pour éviter la requête statique ---
        queryset=None,
        # ------------------------------------------------------------------------------------
        widget=forms.SelectMultiple(attrs={'size': 10, 'class': 'form-control'}),
        label="Utilisateurs à exporter",
        help_text="Maintenez Ctrl (Cmd sur Mac) pour sélectionner plusieurs utilisateurs"
    )
    
    format_export = forms.ChoiceField(
        choices=[
            ('pdf', 'PDF (optimisé pour impression)'),
            ('csv', 'CSV (compatible tous logiciels)'),
            ('excel', 'Excel (.xlsx moderne)'),
        ],
        initial='excel',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Format d'export",
        help_text="Excel .xlsx est recommandé pour une meilleure compatibilité"
    )
    
    tri = forms.ChoiceField(
        choices=[
            ('nom', 'Par nom (A-Z)'),
            ('matricule', 'Par matricule'),
            # ('service', 'Par service'),  # Retiré temporairement
            ('mds', 'Par MDS principale'),
        ],
        initial='nom',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Tri des données",
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # --- DÉPLACEMENT DE LA REQUÊTE : Chargement dynamique dans __init__ ---
        self.fields['utilisateurs'].queryset = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        # ----------------------------------------------------------------------
        
        # Personnalisation des labels
        self.fields['utilisateurs'].label_suffix = ''
