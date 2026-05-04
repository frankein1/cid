# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

"""
ged/forms.py - VERSION POLIE CORE-DITAS 2026
Maintien de toute la logique métier originale avec compatibilité Capacités.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import DocumentGED, DocumentType, DocumentCategorie

class DocumentGEDForm(forms.ModelForm):
    # Champ virtuel pour l'upload
    file = forms.FileField(
        label="Fichier",
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
        })
    )
    
    type_document = forms.ModelChoiceField(
        queryset=DocumentType.objects.filter(actif=True),  # Tous les types actifs
        label="Type de document",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = DocumentGED
        # Inclusion de date_expiration pour la gestion des alertes
        fields = [
            'type_document', 'titre', 'description', 
            'date_expiration', 'confidentialite', 'agents_autorises'
        ]
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre descriptif du document'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_expiration': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'confidentialite': forms.Select(attrs={'class': 'form-select'}),
            'agents_autorises': forms.SelectMultiple(attrs={'class': 'form-select select2'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Si on est en édition, le fichier n'est plus obligatoire
        if self.instance.pk:
            self.fields['file'].required = False
            self.fields['file'].help_text = "Laissez vide pour conserver le fichier actuel."
        
        if user:
            # SÉCURITÉ 2026 : Utilisation des Capacités CORE
            if not user.a_la_capacite('peut_valider'):
                # Restriction des choix de confidentialité seulement
                # Les agents standards ne peuvent pas choisir TRES_CONFIDENTIEL
                choices = [c for c in DocumentGED.CONF_CHOICES if c[0] != 'TRES_CONFIDENTIEL']
                self.fields['confidentialite'].choices = choices
            
            # IMPORTANT : On ne filtre PAS les types de documents
            # Tous les agents voient tous les types actifs
            # La sécurité se fera au niveau de la confidentialité du document
            
            # Le queryset reste : DocumentType.objects.filter(actif=True)
            # Déjà défini dans le champ type_document ci-dessus

    def clean_file(self):
        file = self.cleaned_data.get('file')
        # Validation spécifique si nouveau fichier
        if file:
            # On pourrait ajouter ici une validation globale de sécurité 
            # avant la validation par type
            pass
        return file

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        type_doc = cleaned_data.get('type_document')
        
        # Validation dynamique basée sur les règles du Type de Document
        if file and type_doc:
            # Vérification de la taille (Mo -> Octets)
            if file.size > type_doc.taille_max_mb * 1024 * 1024:
                self.add_error('file', f"Le fichier est trop volumineux pour ce type (max {type_doc.taille_max_mb} Mo).")
            
            # Vérification de l'extension
            ext = file.name.split('.')[-1].lower()
            if type_doc.extensions_autorisees and ext not in type_doc.extensions_autorisees:
                self.add_error('file', f"Extension .{ext} non autorisée. Autorisées : {', '.join(type_doc.extensions_autorisees)}")
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Récupérer le fichier depuis le formulaire
        file = self.cleaned_data.get('file')
        if file:
            # Stocker le fichier pour le traitement ultérieur
            instance._uploaded_file = file
            
            # Définir les métadonnées
            instance.taille_octets = file.size
            instance.extension = file.name.split('.')[-1].lower() if '.' in file.name else ''
            
            # Générer un titre par défaut si vide
            if not instance.titre and file.name:
                instance.titre = file.name
        
        if commit:
            instance.save()
            self.save_m2m()
        
        return instance


class DocumentTypeForm(forms.ModelForm):
    class Meta:
        model = DocumentType
        fields = [
            'code', 'nom', 'categorie', 'extensions_autorisees', 
            'taille_max_mb', 'est_sensible', 'actif'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'categorie': forms.Select(attrs={'class': 'form-select'}),
            'extensions_autorisees': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'pdf, jpg, png (séparés par des virgules)'
            }),
            'taille_max_mb': forms.NumberInput(attrs={'class': 'form-control'}),
            'est_sensible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_extensions_autorisees(self):
        data = self.cleaned_data.get('extensions_autorisees')
        if isinstance(data, str):
            # Nettoyage propre : minuscules, sans points, sans espaces
            extensions = [ext.strip().lower().replace('.', '') for ext in data.split(',') if ext.strip()]
            return extensions
        return data
