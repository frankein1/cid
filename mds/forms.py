# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# mds/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import MDS, UserMDSProfile, MDSReception
from core.models.profil import Profil

User = get_user_model()

# ================================================================
# 1. FORMULAIRE STRUCTURE MDS
# ================================================================
class MDSForm(forms.ModelForm):
    class Meta:
        model = MDS
        fields = ['code_mds', 'nom', 'adresse', 'code_postal', 'ville', 
                 'telephone', 'email', 'responsable', 'active',
                 'nb_agents_max', 'services_proposes', 'communes',
                 'latitude', 'longitude', 'configuration']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    # Filtrage responsable : utilisateurs ayant un profil avec la capacité "peut_administrer"
        self.fields['responsable'].queryset = User.objects.filter(
            profils__capacites__code='peut_valider',  # ✅ Correct
            is_active=True
        ).distinct().order_by('last_name')
    
        common_class = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': common_class})

# ================================================================
# 2. FORMULAIRE AJOUT AGENT (HYBRIDE : EXISTANT OU NOUVEAU)
# ================================================================
class UserMDSProfileForm(forms.ModelForm):
    mode = forms.ChoiceField(
        choices=[('existant', 'Agent existant'), ('nouveau', 'Créer un nouvel agent')],
        widget=forms.RadioSelect(),
        initial='existant',
        label="Origine de l'agent"
    )
    user_existant = forms.ModelChoiceField(
        queryset=User.objects.none(), 
        required=False,
        label="Agent existant"
    )
    
    # Champs spécifiques pour la création d'un compte
    nouveau_matricule = forms.CharField(required=False, max_length=20)
    nouveau_prenom = forms.CharField(required=False, max_length=30)
    nouveau_nom = forms.CharField(required=False, max_length=30)
    nouveau_email = forms.EmailField(required=False)
    nouveau_mdp1 = forms.CharField(required=False, widget=forms.PasswordInput)
    nouveau_mdp2 = forms.CharField(required=False, widget=forms.PasswordInput)
    
    # Profil métier CORE obligatoire pour les nouveaux et existants
    profil_core = forms.ModelChoiceField(
        queryset=Profil.objects.filter(code__startswith='MDS_').order_by('nom'),
        required=True,
        label="Profil métier (CORE)"
    )

    class Meta:
        model = UserMDSProfile
        fields = ['date_debut', 'date_fin', 'principale', 'actif', 'role_specifique', 
                 'bureau', 'telephone_interne', 'peut_gerer_utilisateurs']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.mds = kwargs.pop('mds', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Date du jour par défaut pour les remplacements/arrivées
        if not self.instance.pk:
            self.initial['date_debut'] = timezone.now().date()
            self.initial['actif'] = True

        # Liste des agents non encore rattachés à cette MDS spécifique
        if self.mds:
    # Inclure les utilisateurs qui ont un profil INACTIF pour cette MDS
    # Ils pourront ainsi être réactivés plutôt que de créer un doublon
            deja_presents_actifs = UserMDSProfile.objects.filter(mds=self.mds, actif=True).values_list('user_id', flat=True)
    
            self.fields['user_existant'].queryset = User.objects.exclude(id__in=deja_presents_actifs).order_by('last_name')

        # Application du style Tailwind
        common_class = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        for name, field in self.fields.items():
            if name != 'mode' and not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs.update({'class': common_class})

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('mode')
        if mode == 'nouveau':
            # Validation minimale pour le nouveau compte
            if not cleaned_data.get('nouveau_matricule'):
                self.add_error('nouveau_matricule', "Le matricule est obligatoire pour un nouveau compte.")
            if cleaned_data.get('nouveau_mdp1') != cleaned_data.get('nouveau_mdp2'):
                self.add_error('nouveau_mdp2', "Les mots de passe ne correspondent pas.")
        elif mode == 'existant' and not cleaned_data.get('user_existant'):
            self.add_error('user_existant', "Veuillez sélectionner un agent dans la liste.")
        return cleaned_data

# ================================================================
# 3. FORMULAIRE MISE À JOUR AGENT
# ================================================================
class UserMDSProfileUpdateForm(forms.ModelForm):
    # ✅ AJOUT du champ profil_core
    profil_core = forms.ModelChoiceField(
        queryset=Profil.objects.filter(code__startswith='MDS_').order_by('nom'),
        required=False,  # Optionnel en modification
        label="Profil métier (CORE)"
    )
    
    class Meta:
        model = UserMDSProfile
        fields = ['date_debut', 'date_fin', 'principale', 'actif', 'role_specifique', 
                 'bureau', 'telephone_interne', 'peut_gerer_utilisateurs']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_class = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': common_class})

# ================================================================
# 4. FORMULAIRES RÉCEPTION
# ================================================================
class MDSReceptionForm(forms.ModelForm):
    class Meta:
        model = MDSReception
        fields = [
            'nom', 'type_salle', 'capacite', 'actif', 
            'horaire_debut', 'horaire_fin',
            # ✅ AJOUT des champs de disponibilité hebdomadaire
            'disponible_lundi', 'disponible_mardi', 'disponible_mercredi',
            'disponible_jeudi', 'disponible_vendredi', 'disponible_samedi',
            'disponible_dimanche'
        ]
        widgets = {
            'horaire_debut': forms.TimeInput(attrs={'type': 'time'}),
            'horaire_fin': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_class = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': common_class})
