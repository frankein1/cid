# AidFi/forms/f_regie.py ← FIX import
from django import forms
from AidFi.models.m_regie import RegieUrgence  # ✅ Import DIRECT

class RegieUrgenceForm(forms.ModelForm):
    class Meta:
        model = RegieUrgence
        fields = ['montant_urgence', 'motif_urgence', 'date_rendez_vous_regie', 'regisseur']
        widgets = {
            'montant_urgence': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'motif_urgence': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_rendez_vous_regie': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'regisseur': forms.TextInput(attrs={'class': 'form-control'}),
        }
