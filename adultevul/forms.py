# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# adultevul/forms.py
from django import forms
from django.contrib.auth import get_user_model

from mds.models import UserMDSProfile
from .models import (
    CelluleEvaluation, MesureMASP, MODALITES, PROPOSITIONS, SituationAdulteVulnerable, URGENCES,
)

User = get_user_model()
CHAMP = {'class': 'mt-1 block w-full rounded-lg border-gray-300'}


class SituationForm(forms.ModelForm):
    """Recueil de l'information (annexe 1)."""
    elements = forms.MultipleChoiceField(
        label="Éléments de l'information", required=False, widget=forms.CheckboxSelectMultiple,
        choices=[('CARENCE', 'Carence de soins'), ('MALT_PHYS', 'Maltraitance physique'),
                 ('MALT_PSY', 'Maltraitance psychologique'), ('AUTRE', 'Autres')])

    class Meta:
        model = SituationAdulteVulnerable
        fields = [
            'date_reception', 'mode_recueil', 'origine', 'institution', 'signalant_nom', 'signalant_qualite',
            'signalant_contact', 'signalant_connait_personne', 'signalant_confirmation_ecrite',
            'intervenants_actuels', 'elements', 'danger_immediat', 'faits', 'evenement_declencheur',
            'depuis_quand', 'sante', 'conditions_vie', 'personne_nom', 'personne_prenom', 'personne_naissance',
            'personne_adresse', 'personne_hebergee', 'famille', 'mds',
        ]
        widgets = {
            'date_reception': forms.DateInput(attrs={'type': 'date', **CHAMP}),
            'personne_naissance': forms.DateInput(attrs={'type': 'date', **CHAMP}),
            'faits': forms.Textarea(attrs={'rows': 6, **CHAMP}),
            'intervenants_actuels': forms.Textarea(attrs={'rows': 2, **CHAMP}),
            'evenement_declencheur': forms.Textarea(attrs={'rows': 2, **CHAMP}),
            'signalant_contact': forms.Textarea(attrs={'rows': 2, **CHAMP}),
            'sante': forms.Textarea(attrs={'rows': 2, **CHAMP}),
            'conditions_vie': forms.Textarea(attrs={'rows': 2, **CHAMP}),
            'personne_adresse': forms.Textarea(attrs={'rows': 2, **CHAMP}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        mds_ids = None
        if user is not None and not user.is_superuser and not user.a_la_capacite('peut_administrer'):
            mds_ids = list(UserMDSProfile.objects.filter(user=user, actif=True).values_list('mds_id', flat=True))
        from mds.models import MDS
        self.fields['mds'].queryset = MDS.objects.filter(pk__in=mds_ids) if mds_ids is not None else MDS.objects.all()
        self.fields['mds'].label = "MDS compétente (lieu d'habitation ou d'hébergement)"
        self.fields['famille'].label = "Dossier de la personne dans CID (facultatif)"
        self.fields['mds'].required = True
        for nom, champ in self.fields.items():
            if not isinstance(champ.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                champ.widget.attrs.setdefault('class', CHAMP['class'])


class QualificationForm(forms.Form):
    qualifiee = forms.TypedChoiceField(
        label="Décision du cadre", coerce=lambda v: v == 'oui',
        choices=[('oui', "Information préoccupante qualifiée : mettre en place la cellule d'évaluation"),
                 ('non', 'Non qualifiée (mise à disposition, liaison ou clôture)')],
        widget=forms.RadioSelect)
    motif = forms.CharField(label="Motif", widget=forms.Textarea(attrs={'rows': 3, **CHAMP}))


class CelluleForm(forms.ModelForm):
    """Cellule d'évaluation (annexe 2) : composition, référents, plan d'action, propositions."""
    propositions = forms.MultipleChoiceField(
        label="Propositions", required=False, widget=forms.CheckboxSelectMultiple,
        choices=PROPOSITIONS)
    referents = forms.ModelMultipleChoiceField(
        label="Référent(s) de la situation", queryset=User.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = CelluleEvaluation
        fields = ['date_cellule', 'urgence', 'participants', 'referents', 'modalites', 'modalites_precision',
                  'investigations', 'plan_action', 'propositions', 'argumentation']
        widgets = {
            'date_cellule': forms.DateInput(attrs={'type': 'date', **CHAMP}),
            'participants': forms.Textarea(attrs={'rows': 3, **CHAMP}),
            'investigations': forms.Textarea(attrs={'rows': 3, **CHAMP}),
            'plan_action': forms.Textarea(attrs={'rows': 4, **CHAMP}),
            'argumentation': forms.Textarea(attrs={'rows': 4, **CHAMP}),
            'urgence': forms.Select(attrs=CHAMP),
            'modalites': forms.Select(attrs=CHAMP),
            'modalites_precision': forms.TextInput(attrs=CHAMP),
        }

    def __init__(self, *args, mds=None, **kwargs):
        super().__init__(*args, **kwargs)
        if mds is not None:
            ids = UserMDSProfile.objects.filter(mds=mds, actif=True).values_list('user_id', flat=True)
            self.fields['referents'].queryset = User.objects.filter(pk__in=ids, is_active=True).order_by('last_name', 'username')
        self.fields['urgence'].choices = URGENCES
        self.fields['modalites'].choices = MODALITES
        self.fields['propositions'].initial = self.instance.propositions if self.instance.pk else []

    def clean_propositions(self):
        return list(self.cleaned_data.get('propositions') or [])


class RenvoiForm(forms.Form):
    motif = forms.CharField(label="Motif du renvoi (compléments demandés)", widget=forms.Textarea(attrs={'rows': 3, **CHAMP}))


class MotifForm(forms.Form):
    commentaire = forms.CharField(label="Décision administrative", widget=forms.Textarea(attrs={'rows': 4, **CHAMP}))


class ProtectionForm(forms.ModelForm):
    """Protection juridique (annexe 9) : parquet, mesure et pièces exigées."""
    class Meta:
        model = SituationAdulteVulnerable
        fields = ['tribunal', 'mesure_protection', 'pj_acte_naissance', 'pj_fiche', 'pj_certificat',
                  'pj_certificat_absence']
        widgets = {'pj_certificat_absence': forms.Textarea(attrs={'rows': 3, **CHAMP})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tribunal'].widget.attrs.update(CHAMP)
        self.fields['mesure_protection'].widget.attrs.update(CHAMP)


class MaspForm(forms.ModelForm):
    """Suivi MASP (annexe 6) : niveau, dates et référent."""
    class Meta:
        model = MesureMASP
        fields = ['niveau', 'date_demande', 'date_debut', 'date_echeance', 'date_reevaluation',
                  'referent_nom', 'referent_qualite', 'notes']
        widgets = {
            'date_demande': forms.DateInput(attrs={'type': 'date', **CHAMP}),
            'date_debut': forms.DateInput(attrs={'type': 'date', **CHAMP}),
            'date_echeance': forms.DateInput(attrs={'type': 'date', **CHAMP}),
            'date_reevaluation': forms.DateInput(attrs={'type': 'date', **CHAMP}),
            'notes': forms.Textarea(attrs={'rows': 4, **CHAMP}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            champ.widget.attrs.setdefault('class', CHAMP['class'])
