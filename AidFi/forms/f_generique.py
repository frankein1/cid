# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/forms/f_generique.py

from django import forms
from django.forms import ModelForm
from ..models.m_generique import DemandeAide, PieceJustificative

class DemandeAideForm(ModelForm):
    class Meta:
        model = DemandeAide
        fields = ['type_aide', 'motif_demande', 'montant_sollicite', 'evaluation_sociale']
        widgets = {'evaluation_sociale': forms.Textarea(attrs={"rows": 4, "class": "textarea"})}

class PieceJustificativeForm(ModelForm):
    class Meta:
        model = PieceJustificative
        fields = ['type_piece', 'document_ged']
