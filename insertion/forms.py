# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/forms.py
from django import forms

from insertion.models import ActionInsertion, PoleInsertion, TypeActionInsertion

CHAMP = "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"


class ActionInsertionForm(forms.ModelForm):
    class Meta:
        model = ActionInsertion
        fields = ['code', 'libelle', 'type_action', 'niveau', 'mds', 'poles', 'territoire', 'porteur', 'partenaire',
                  'public_vise', 'description', 'duree', 'destinataires', 'pieces_a_joindre', 'comite_suivi',
                  'rythme_comite', 'aussi_logement', 'actif']
        widgets = {
            'public_vise': forms.Textarea(attrs={'rows': 2}), 'description': forms.Textarea(attrs={'rows': 3}),
            'destinataires': forms.Textarea(attrs={'rows': 2}), 'pieces_a_joindre': forms.Textarea(attrs={'rows': 2}),
            'poles': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, user=None, mds_possibles=None, departemental_possible=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type_action'].queryset = TypeActionInsertion.objects.filter(actif=True)
        self.fields['poles'].queryset = PoleInsertion.objects.filter(actif=True)
        self.fields['mds'].queryset = mds_possibles
        if not departemental_possible:
            self.fields['niveau'].choices = [(ActionInsertion.LOCAL, "Locale (MDS)")]
            self.fields['niveau'].initial = ActionInsertion.LOCAL
            del self.fields['poles']          # une action locale couvre sa MDS
        if mds_possibles is None or not mds_possibles.exists():
            self.fields['niveau'].choices = [(ActionInsertion.DEPARTEMENTAL, "Départementale")]
            del self.fields['mds']            # pas d'action locale possible pour cette personne
        for nom, champ in self.fields.items():
            if not isinstance(champ.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                champ.widget.attrs.setdefault('class', CHAMP)

    def clean(self):
        donnees = super().clean()
        niveau, mds, code = donnees.get('niveau'), donnees.get('mds'), donnees.get('code')
        if 'mds' not in self.fields:
            donnees['mds'] = None
        if niveau == ActionInsertion.DEPARTEMENTAL:
            donnees['mds'] = None
        elif not mds:
            self.add_error('mds', "Choisissez la MDS de cette action locale.")
        if code:
            doublon = ActionInsertion.objects.filter(code=code, mds=donnees.get('mds')).exclude(pk=self.instance.pk)
            if doublon.exists():
                self.add_error('code', "Ce code est déjà utilisé" + (" dans cette MDS." if donnees.get('mds') else "."))
        return donnees


class ImportCSVForm(forms.Form):
    fichier = forms.FileField(label="Fichier CSV", widget=forms.ClearableFileInput(attrs={'accept': '.csv,text/csv'}))
