"""
Champs de formulaire personnalisés pour beneficiaire
Fichier : beneficiaire/fields.py
"""

from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import re
from datetime import datetime

# =============================================================================
# CHAMP TÉLÉPHONE avec formatage automatique
# =============================================================================

class TelephoneField(forms.CharField):
    """
    Champ pour les numéros de téléphone français
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 15)
        kwargs.setdefault('required', False)
        super().__init__(*args, **kwargs)
        self.help_text = "Format : 10 chiffres (espaces optionnels)"
    
    def clean(self, value):
        if not value:
            if self.required:
                raise ValidationError("Ce champ est obligatoire")
            return ''
        
        value_clean = re.sub(r'[\s\.\-]', '', value)
        
        if not value_clean.isdigit():
            raise ValidationError("Le numéro ne doit contenir que des chiffres")
        
        if len(value_clean) != 10:
            raise ValidationError("Le numéro doit contenir exactement 10 chiffres")
        
        if not value_clean.startswith('0'):
            raise ValidationError("Le numéro doit commencer par 0")
        
        return value_clean
    
    def prepare_value(self, value):
        if not value:
            return value
        
        value_clean = re.sub(r'\s', '', str(value))
        
        if len(value_clean) == 10 and value_clean.isdigit():
            return f"{value_clean[0:2]} {value_clean[2:4]} {value_clean[4:6]} {value_clean[6:8]} {value_clean[8:10]}"
        
        return value

# =============================================================================
# CHAMP DATE avec saisie simplifiée et conversion automatique
# =============================================================================

class DateSimplifieeField(forms.DateField):
    """
    Champ de date avec saisie simplifiée et conversion automatique
    
    Formats acceptés :
    - 01012025 (JJMMAAAA)
    - 010125 (JJMMAA → JJMM2005 si <50, JJMM1905 si >=50)
    - 030303 (JJMMAA → 03/03/2003)
    - 01/01/2025 (format classique)
    - 01-01-2025 (avec tirets)
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', False)
        super().__init__(*args, **kwargs)
        self.help_text = "Formats: JJMMAAAA (01012025) ou JJMMAA (010125) ou JJ/MM/AAAA"
    
    def clean(self, value):
        """
        Convertir la saisie utilisateur en date avec conversion automatique
        """
        if not value:
            if self.required:
                raise ValidationError("Ce champ est obligatoire")
            return None
        
        # Si c'est déjà un objet date, on le retourne
        if isinstance(value, datetime):
            return value.date()
        
        # Convertir en chaîne
        value_str = str(value).strip()
        
        # Si vide après nettoyage
        if not value_str:
            if self.required:
                raise ValidationError("Ce champ est obligatoire")
            return None
        
        # Supprimer les séparateurs (/, -, espaces, points)
        value_clean = re.sub(r'[/\-\s\.]', '', value_str)
        
        # Vérifier que ce sont des chiffres
        if not value_clean.isdigit():
            raise ValidationError("Format invalide. Utilisez JJMMAAAA (ex: 01012025) ou JJMMAA (ex: 010125)")
        
        # Parser selon la longueur
        try:
            if len(value_clean) == 8:
                # Format JJMMAAAA
                jour = int(value_clean[0:2])
                mois = int(value_clean[2:4])
                annee = int(value_clean[4:8])
            
            elif len(value_clean) == 6:
                # Format JJMMAA - Conversion automatique intelligente
                jour = int(value_clean[0:2])
                mois = int(value_clean[2:4])
                annee_courte = int(value_clean[4:6])
                
                # CONVERSION AUTOMATIQUE : Si année < 50 → 20xx, sinon → 19xx
                # Exemple: 030303 → 03/03/2003, 031253 → 03/12/1953
                if annee_courte < 50:
                    annee = 2000 + annee_courte
                else:
                    annee = 1900 + annee_courte
            
            elif len(value_clean) == 4:
                # Format JJMM - on suppose l'année courante
                jour = int(value_clean[0:2])
                mois = int(value_clean[2:4])
                annee = datetime.now().year
                
            else:
                raise ValidationError(
                    f"Format invalide ({len(value_clean)} chiffres). "
                    "Utilisez 4 chiffres (JJMM), 6 chiffres (JJMMAA) ou 8 chiffres (JJMMAAAA)"
                )
            
            # Créer l'objet date (cela valide aussi la date)
            date_obj = datetime(annee, mois, jour).date()
            return date_obj
        
        except ValueError as e:
            raise ValidationError(
                f"Date invalide : {value_str}. "
                "Vérifiez le jour (1-31), mois (1-12) et année."
            )
    
    def prepare_value(self, value):
        """
        Préparer l'affichage de la date au format français
        """
        if not value:
            return value
        
        # Si c'est une chaîne, on essaie de la parser
        if isinstance(value, str):
            try:
                cleaned = self.clean(value)
                if cleaned:
                    return cleaned.strftime('%d/%m/%Y')
            except:
                return value
        
        # Si c'est un objet date
        if hasattr(value, 'strftime'):
            return value.strftime('%d/%m/%Y')
        
        return value

# =============================================================================
# WIDGETS
# =============================================================================

class TelephoneWidget(forms.TextInput):
    """
    Widget pour le champ téléphone
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'placeholder': '06 12 34 56 78',
            'class': 'telephone-input',
            'maxlength': '14',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

class DateSimplifieeWidget(forms.TextInput):
    """
    Widget pour le champ date simplifiée
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'placeholder': 'JJMMAAAA (01012025) ou JJMMAA (010125)',
            'class': 'date-input',
            'maxlength': '10',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
