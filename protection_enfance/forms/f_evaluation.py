# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/forms/f_evaluation.py
from django import forms

from protection_enfance.forms.f_ip import CSS, _styler
from protection_enfance.models import ActionIP, EnfantIP, RapportIP, SaisineIP
from protection_enfance.models.m_evaluation import RESULTATS, TYPES_ACTION, TYPES_AUDITION, TYPES_COURRIER


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
        # Auditions et convocations ont leur propre formulaire (une case par personne, courriers automatiques)
        self.fields['type_action'].choices = [(c, l) for c, l in TYPES_ACTION
                                              if c not in TYPES_AUDITION + TYPES_COURRIER]
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


def _libelle_adulte(a):
    tags = [t for t, ok in (("autorité parentale", a.autorite_parentale), ("héberge les enfants", a.heberge_enfants))
            if ok]
    return f"{a}" + (f" ({', '.join(tags)})" if tags else "") + (f" – {a.commentaire}" if a.commentaire else "")


def _datetime_widget():
    return forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')


class AuditionForm(forms.Form):
    """
    Audition des parents (une case par adulte) ou des enfants (une case par enfant, même créneau).
    Les courriers de convocation sont produits dès l'enregistrement.
    """
    type_action = forms.ChoiceField(label="Audition", choices=[
        ('AUDITION_PARENTS', "Audition des parents"),
        ('AUDITION_ENFANT', "Audition des enfants (même heure, reçus un par un)")])
    date = forms.DateTimeField(label="Date et heure", widget=_datetime_widget())
    duree_minutes = forms.IntegerField(label="Durée (min)", min_value=10, initial=60)
    adultes = forms.ModelMultipleChoiceField(label="Adultes convoqués", queryset=None, required=False,
                                             widget=forms.CheckboxSelectMultiple)
    enfants = forms.ModelMultipleChoiceField(label="Enfants convoqués", queryset=None, required=False,
                                             widget=forms.CheckboxSelectMultiple)
    participants = forms.ModelMultipleChoiceField(label="Professionnels", queryset=None, required=False,
                                                  widget=forms.CheckboxSelectMultiple)
    ajouter_agenda = forms.BooleanField(label="Inscrire dans l'agenda des professionnels", required=False,
                                        initial=True)

    def __init__(self, *args, ip=None, professionnels=None, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import User
        self.fields['adultes'].queryset = ip.adultes.all()
        self.fields['enfants'].queryset = ip.enfants.all()
        self.fields['participants'].queryset = User.objects.filter(
            pk__in=[u.pk for u in (professionnels or [])]).order_by('last_name')
        self.fields['participants'].label_from_instance = lambda u: u.get_full_name() or u.username
        self.fields['adultes'].label_from_instance = _libelle_adulte
        self.fields['enfants'].label_from_instance = lambda e: (
            f"{e.prenom} {e.nom.upper()}" + (f" – vit chez {e.heberge_par.prenom} {e.heberge_par.nom.upper()}"
                                             if e.heberge_par_id else " – « vit chez » à renseigner"))
        if not self.is_bound:
            self.initial.setdefault('adultes', [a.pk for a in ip.adultes.all() if a.convoque])
            self.initial.setdefault('enfants', [e.pk for e in ip.enfants.all()])
        _styler(self)

    def clean_date(self):
        from django.utils import timezone
        d = self.cleaned_data['date']
        if d <= timezone.now():
            raise forms.ValidationError("La convocation porte sur une date à venir.")
        return d


class ConclusionEnfantForm(forms.ModelForm):
    """Conclusion de l'évaluation pour un enfant : en danger / en risque / pas en danger + types de danger."""
    class Meta:
        model = EnfantIP
        fields = ['conclusion', 'dangers_constates', 'conclusion_commentaire']
        widgets = {'conclusion': forms.RadioSelect, 'dangers_constates': forms.CheckboxSelectMultiple,
                   'conclusion_commentaire': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from protection_enfance.models import TypeDanger
        qs = TypeDanger.objects.filter(actif=True)
        if self.instance.pk:
            qs = (qs | self.instance.dangers_constates.all()).distinct()
        self.fields['dangers_constates'].queryset = qs
        self.fields['conclusion'].choices = [c for c in self.fields['conclusion'].choices if c[0]]
        self.fields['conclusion'].required = False
        _styler(self)
