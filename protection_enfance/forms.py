# protection_enfance/forms.py
from django import forms


class InformationPreoccupanteForm(forms.Form):
enfant_nom = forms.CharField(required=False)
enfant_date_naissance = forms.DateField(required=False)
origine = forms.ChoiceField(choices=[('MDS','MDS'),('PARTENAIRE','Partenaire'),('NUM_ENFANCE','Numéro Enfance')])
description = forms.CharField(widget=forms.Textarea)
