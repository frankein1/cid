# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/forms.py
from django import forms


class InformationPreoccupanteForm(forms.Form):
enfant_nom = forms.CharField(required=False)
enfant_date_naissance = forms.DateField(required=False)
origine = forms.ChoiceField(choices=[('MDS','MDS'),('PARTENAIRE','Partenaire'),('NUM_ENFANCE','Numéro Enfance')])
description = forms.CharField(widget=forms.Textarea)
