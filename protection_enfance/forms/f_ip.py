# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/forms/f_ip.py
from django import forms
from django.forms import inlineformset_factory

from protection_enfance.models import AdulteIP, EnfantIP, InformationPreoccupante, TypeDanger

CSS = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 text-sm'


def _styler(form):
    for f in form.fields.values():
        if not isinstance(f.widget, (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)):
            f.widget.attrs.setdefault('class', CSS)


class IPForm(forms.ModelForm):
    """Saisie de l'IP par la CRIP."""
    code_famille = forms.CharField(
        label="Code du dossier famille dans CID", required=False, max_length=20,
        help_text="Code interne d'un parent (ex. MDSTEST1-0001). Laissez vide si la famille n'a pas de dossier.")

    class Meta:
        model = InformationPreoccupante
        fields = ['date_reception_crip', 'origine', 'niveau_urgence', 'description', 'situation_particuliere',
                  'signalant_nom', 'signalant_qualite', 'signalant_structure', 'signalant_contact',
                  'signalant_confidentialite', 'famille_libelle', 'famille_adresse', 'mds', 'mds_partage',
                  'autre_departement', 'dangers_signales']
        widgets = {
            'date_reception_crip': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 6}),
            'signalant_contact': forms.Textarea(attrs={'rows': 2}),
            'famille_adresse': forms.Textarea(attrs={'rows': 2}),
            'mds_partage': forms.SelectMultiple(attrs={'size': 4}),
            'dangers_signales': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from mds.models import MDS
        self.fields['mds'].queryset = MDS.objects.filter(active=True).order_by('nom')
        self.fields['mds_partage'].queryset = MDS.objects.filter(active=True).order_by('nom')
        self.fields['mds'].required = False
        self.fields['dangers_signales'].queryset = TypeDanger.objects.filter(actif=True) | (
            self.instance.dangers_signales.all() if self.instance.pk else TypeDanger.objects.none())
        self.fields['dangers_signales'].queryset = self.fields['dangers_signales'].queryset.distinct()
        if self.instance.pk and self.instance.famille_id:
            self.fields['code_famille'].initial = self.instance.famille.code_interne
        _styler(self)

    def clean_code_famille(self):
        code = (self.cleaned_data.get('code_famille') or '').strip()
        if not code:
            return None
        from beneficiaire.models import Beneficiaire
        famille = Beneficiaire.objects.filter(code_interne__iexact=code).select_related('mds').first()
        if not famille:
            raise forms.ValidationError("Aucun dossier CID avec ce code.")
        return famille

    def clean(self):
        cd = super().clean()
        famille = cd.get('code_famille')
        if not famille and not (cd.get('famille_libelle') or '').strip():
            self.add_error('famille_libelle', "Indiquez le dossier CID de la famille ou, à défaut, son nom.")
        if famille and not cd.get('mds') and famille.mds_id:
            cd['mds'] = famille.mds
        return cd

    def save(self, commit=True):
        ip = super().save(commit=False)
        ip.famille = self.cleaned_data.get('code_famille')
        if not ip.mds_id and self.cleaned_data.get('mds'):
            ip.mds = self.cleaned_data['mds']
        if commit:
            ip.save()
            self.save_m2m()
        return ip


class EnfantForm(forms.ModelForm):
    class Meta:
        model = EnfantIP
        fields = ['prenom', 'nom', 'date_naissance']
        widgets = {'date_naissance': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _styler(self)


EnfantFormSet = inlineformset_factory(InformationPreoccupante, EnfantIP, form=EnfantForm,
                                      extra=2, can_delete=True)


class AdulteForm(forms.ModelForm):
    class Meta:
        model = AdulteIP
        fields = ['qualite', 'civilite', 'prenom', 'nom', 'adresse', 'code_postal', 'ville', 'telephone', 'mds',
                  'autorite_parentale', 'heberge_enfants', 'convoque', 'commentaire']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from mds.models import MDS
        self.fields['mds'].queryset = MDS.objects.filter(active=True).order_by('nom')
        self.fields['mds'].required = False
        self.fields['prenom'].required = False
        _styler(self)

    def clean(self):
        cd = super().clean()
        # À la création, autorité parentale ou hébergement ⇒ convoqué d'office (décochable ensuite)
        if not self.instance.pk and (cd.get('autorite_parentale') or cd.get('heberge_enfants')):
            cd['convoque'] = True
        return cd


AdulteFormSet = inlineformset_factory(InformationPreoccupante, AdulteIP, form=AdulteForm, extra=1, can_delete=True)


class EnfantFamilleForm(forms.ModelForm):
    """Enfant dans la composition familiale : identité et « vit chez »."""
    class Meta:
        model = EnfantIP
        fields = ['prenom', 'nom', 'date_naissance', 'heberge_par']
        widgets = {'date_naissance': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, adultes=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['heberge_par'].queryset = adultes if adultes is not None else AdulteIP.objects.none()
        self.fields['heberge_par'].required = False
        _styler(self)


class _BaseEnfantFamille(forms.BaseInlineFormSet):
    def __init__(self, *args, adultes=None, **kwargs):
        self._adultes = adultes
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kw = super().get_form_kwargs(index)
        kw['adultes'] = self._adultes
        return kw


EnfantFamilleFormSet = inlineformset_factory(InformationPreoccupante, EnfantIP, form=EnfantFamilleForm,
                                             formset=_BaseEnfantFamille, extra=1, can_delete=True)


class BinomeForm(forms.Form):
    referent_1 = forms.ModelChoiceField(queryset=None, label="Référent 1")
    referent_2 = forms.ModelChoiceField(queryset=None, label="Référent 2")

    def __init__(self, *args, candidats=None, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import User
        qs = User.objects.filter(pk__in=[u.pk for u in (candidats or [])]).order_by('last_name', 'first_name')
        for f in ('referent_1', 'referent_2'):
            self.fields[f].queryset = qs
            self.fields[f].label_from_instance = lambda u: u.get_full_name() or u.username
            self.fields[f].widget.attrs['class'] = CSS
