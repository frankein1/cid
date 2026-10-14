# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/forms/f_cap.py
from django import forms


# =============================================================================
# CAP - CHÈQUES SERVICE (circuit complet)
# =============================================================================
from AidFi.models.m_cap import DemandeCAP, ReceptionCAP

CSS = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500'


def _multiple_de_10(valeur):
    if valeur is None or valeur <= 0 or valeur % 10:
        raise forms.ValidationError("Le montant doit être un multiple de 10 € (10, 20, 30, 40...).")
    return valeur


class DemandeCAPForm(forms.Form):
    """Demande de l'AS : légère, pour une urgence."""
    montant = forms.IntegerField(label="Montant demandé (€)", min_value=10, widget=forms.NumberInput(
        attrs={'class': CSS, 'step': 10, 'min': 10}))
    motivation = forms.CharField(label="Situation et motivation", widget=forms.Textarea(
        attrs={'class': CSS, 'rows': 5}))
    remise_paierie = forms.BooleanField(
        label="Remise exceptionnelle par la paierie départementale (Marseille)", required=False)

    def clean_montant(self):
        return _multiple_de_10(self.cleaned_data['montant'])


class DecisionCAPForm(forms.Form):
    DECISIONS = [('ACCORD', 'Accorder'), ('REFUS', 'Refuser')]
    decision = forms.ChoiceField(choices=DECISIONS, widget=forms.RadioSelect)
    montant_accorde = forms.IntegerField(label="Montant accordé (€)", required=False, min_value=10,
                                         widget=forms.NumberInput(attrs={'class': CSS, 'step': 10, 'min': 10}))
    motif_refus = forms.CharField(label="Motif du refus", required=False,
                                  widget=forms.Textarea(attrs={'class': CSS, 'rows': 3}))

    def clean(self):
        cd = super().clean()
        if cd.get('decision') == 'ACCORD':
            if cd.get('montant_accorde') is None:
                self.add_error('montant_accorde', "Indiquez le montant accordé.")
            else:
                try:
                    _multiple_de_10(cd['montant_accorde'])
                except forms.ValidationError as e:
                    self.add_error('montant_accorde', e)
        elif cd.get('decision') == 'REFUS' and not cd.get('motif_refus'):
            self.add_error('motif_refus', "Le motif est obligatoire en cas de refus.")
        return cd


class ReceptionCAPForm(forms.ModelForm):
    class Meta:
        model = ReceptionCAP
        fields = ['date_reception', 'date_validite', 'reference', 'commentaire']
        widgets = {
            'date_reception': forms.DateInput(attrs={'type': 'date', 'class': CSS}, format='%Y-%m-%d'),
            'date_validite': forms.DateInput(attrs={'type': 'date', 'class': CSS}, format='%Y-%m-%d'),
            'reference': forms.TextInput(attrs={'class': CSS}),
            'commentaire': forms.Textarea(attrs={'class': CSS, 'rows': 2}),
        }


class ClotureCAPForm(forms.Form):
    fichier = forms.FileField(label="Feuille de remise signée (PDF ou photo)",
                              widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}))

    def clean_fichier(self):
        f = self.cleaned_data['fichier']
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Fichier trop volumineux (10 Mo maximum).")
        if not f.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            raise forms.ValidationError("Formats acceptés : PDF, JPG, PNG.")
        return f
