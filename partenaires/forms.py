# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# partenaires/forms.py
from django import forms

from .models import Partenaire


class PartenaireForm(forms.ModelForm):
    class Meta:
        model = Partenaire
        fields = ['organisme', 'service', 'thematique', 'civilite', 'prenom_contact', 'nom_contact', 'fonction',
                  'email', 'telephone', 'adresse', 'code_postal', 'ville', 'commentaire']
        widgets = {'commentaire': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md'

    def clean(self):
        data = super().clean()
        if not (data.get('email') or data.get('telephone')):
            raise forms.ValidationError("Indiquez au moins un e-mail ou un téléphone.")
        return data
