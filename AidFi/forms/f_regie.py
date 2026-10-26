# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/forms/f_regie.py
from django import forms


# =============================================================================
# RÉGIE D'URGENCE – circuit complet
# =============================================================================
CSS = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500'
TAILLE_MAX = 10 * 1024 * 1024


class DemandeRegieForm(forms.Form):
    montant = forms.DecimalField(label="Montant demandé (€)", min_value=1, max_digits=8, decimal_places=2,
                                 widget=forms.NumberInput(attrs={'class': CSS, 'step': '0.01', 'min': 1}))
    motivation = forms.CharField(label="Situation et motif de l'urgence",
                                 widget=forms.Textarea(attrs={'class': CSS, 'rows': 5}))
    mode_paiement = forms.ChoiceField(label="Paiement", widget=forms.RadioSelect,
                                      choices=[("ESPECES", "En espèces à l'usager"),
                                               ("TIERS", "À un tiers (hôtel, fournisseur…)")], initial="ESPECES")
    tiers_nom = forms.CharField(label="Tiers à payer", required=False, max_length=150,
                                widget=forms.TextInput(attrs={'class': CSS, 'placeholder': "Ex. Hôtel du Port"}))
    tiers_reference = forms.CharField(label="Référence de la facture", required=False, max_length=60,
                                      widget=forms.TextInput(attrs={'class': CSS}))
    facture = forms.FileField(label="Facture du tiers", required=False,
                              widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}))
    rib_tiers = forms.FileField(label="RIB du tiers", required=False,
                                widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}))

    def clean(self):
        cd = super().clean()
        if cd.get('mode_paiement') == 'TIERS':
            for champ, message in [('tiers_nom', "Indiquez le tiers à payer."),
                                   ('facture', "La facture du tiers est obligatoire."),
                                   ('rib_tiers', "Le RIB du tiers est obligatoire.")]:
                if not cd.get(champ):
                    self.add_error(champ, message)
        for champ in ('facture', 'rib_tiers'):
            f = cd.get(champ)
            if f and f.size > TAILLE_MAX:
                self.add_error(champ, "Fichier trop volumineux (10 Mo maximum).")
        return cd


class DecisionRegieForm(forms.Form):
    decision = forms.ChoiceField(choices=[('ACCORD', 'Accorder'), ('REFUS', 'Refuser')], widget=forms.RadioSelect)
    montant_accorde = forms.DecimalField(label="Montant accordé (€)", required=False, min_value=1, max_digits=8,
                                         decimal_places=2,
                                         widget=forms.NumberInput(attrs={'class': CSS, 'step': '0.01'}))
    motif_refus = forms.CharField(label="Motif du refus", required=False,
                                  widget=forms.Textarea(attrs={'class': CSS, 'rows': 3}))

    def clean(self):
        cd = super().clean()
        if cd.get('decision') == 'ACCORD' and cd.get('montant_accorde') is None:
            self.add_error('montant_accorde', "Indiquez le montant accordé.")
        if cd.get('decision') == 'REFUS' and not cd.get('motif_refus'):
            self.add_error('motif_refus', "Le motif est obligatoire en cas de refus.")
        return cd
