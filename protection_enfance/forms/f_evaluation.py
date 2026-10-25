# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/forms/f_evaluation.py
from django import forms

from protection_enfance.forms.f_ip import CSS, _styler
from protection_enfance.models import ActionIP, RapportIP, SaisineIP
from protection_enfance.models.m_evaluation import RESULTATS


class ActionForm(forms.ModelForm):
    ajouter_agenda = forms.BooleanField(label="Inscrire dans l'agenda des professionnels", required=False,
                                        initial=True)

    class Meta:
        model = ActionIP
        fields = ['type_action', 'date', 'duree_minutes', 'resultat', 'enfant', 'personnes', 'participants',
                  'date_rdv_propose', 'numero_lrar', 'compte_rendu']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'date_rdv_propose': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'participants': forms.CheckboxSelectMultiple,
            'compte_rendu': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, ip=None, professionnels=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['enfant'].queryset = ip.enfants.all() if ip else self.fields['enfant'].queryset.none()
        self.fields['enfant'].required = False
        from core.models import User
        self.fields['participants'].queryset = User.objects.filter(
            pk__in=[u.pk for u in (professionnels or [])]).order_by('last_name')
        self.fields['participants'].label_from_instance = lambda u: u.get_full_name() or u.username
        self.fields['participants'].required = False
        _styler(self)

    def clean(self):
        cd = super().clean()
        if cd.get('type_action') == 'AUDITION_ENFANT' and not cd.get('enfant'):
            self.add_error('enfant', "Précisez l'enfant entendu.")
        if cd.get('type_action') == 'LRAR' and not (cd.get('numero_lrar') or '').strip():
            self.add_error('numero_lrar', "Le numéro de la LRAR est la preuve de l'envoi : il est obligatoire.")
        return cd


class SuiviActionForm(forms.Form):
    resultat = forms.ChoiceField(choices=RESULTATS)
    compte_rendu = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))
    date_accuse_reception = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))


class RapportForm(forms.ModelForm):
    class Meta:
        model = RapportIP
        fields = ['composition_familiale', 'situation_enfants', 'parole_enfants', 'parole_parents',
                  'conditions_vie', 'partenaires', 'analyse', 'non_cooperation', 'preconisation',
                  'preconisation_detail']
        widgets = {f: forms.Textarea(attrs={'rows': 5}) for f in
                   ['composition_familiale', 'situation_enfants', 'parole_enfants', 'parole_parents',
                    'conditions_vie', 'partenaires', 'analyse', 'preconisation_detail']}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from protection_enfance.models.m_evaluation import RUBRIQUES
        for code, titre in RUBRIQUES:
            self.fields[code].label = titre
        _styler(self)


class SaisineForm(forms.ModelForm):
    class Meta:
        model = SaisineIP
        fields = ['motif', 'danger_imminent']
        widgets = {'motif': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _styler(self)
