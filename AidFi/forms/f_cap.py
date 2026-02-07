# AidFi/forms/f_cap.py ← FIX import
from django import forms
from AidFi.models.m_cap import CAPCheque  # ✅ Import DIRECT depuis models

class CAPAttributionForm(forms.ModelForm):
    class Meta:
        model = CAPCheque
        fields = ['numero_cheque', 'montant', 'date_emission']
        widgets = {
            'numero_cheque': forms.TextInput(attrs={'class': 'form-control'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date_emission': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
