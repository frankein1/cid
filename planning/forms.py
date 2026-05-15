# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

"""
planning/forms.py
VERSION FINALE CORRIGÉE - 12/02/2026
Ajout du champ duree_minutes dans RdvForm
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import CreneauRdv, JourBloque, PermanenceExterne
from mds.models import MDSReception, UserMDSProfile
from django.contrib.auth import get_user_model
User = get_user_model()


class RdvForm(forms.ModelForm):
    class Meta:
        model = CreneauRdv
        fields = ['beneficiaire', 'type_rdv', 'description', 'priorite', 'duree_minutes']

        widgets = {
            'beneficiaire': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'type_rdv': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'priorite': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Objet du rendez-vous, motif, informations importantes...'
            }),
            'duree_minutes': forms.NumberInput(attrs={
                'class': 'w-32 px-3 py-2 border border-gray-300 rounded-md',
                'min': 15,
                'step': 15,
                'placeholder': 'Durée (min)'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.creneau = kwargs.pop('creneau', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if 'beneficiaire' in self.fields:
            from beneficiaire.models import Beneficiaire

            if self.request:
                profile = UserMDSProfile.objects.filter(
                    user=self.request.user, actif=True
                ).first()
                if profile and profile.mds:
                    self.fields['beneficiaire'].queryset = Beneficiaire.objects.filter(
                        mds=profile.mds, actif=True
                    ).order_by('nom', 'prenom')
                else:
                    self.fields['beneficiaire'].queryset = Beneficiaire.objects.filter(
                        actif=True
                    ).order_by('nom', 'prenom')
            else:
                self.fields['beneficiaire'].queryset = Beneficiaire.objects.filter(
                    actif=True
                ).order_by('nom', 'prenom')

        self.fields['beneficiaire'].required = True
        self.fields['type_rdv'].required = True
        self.fields['description'].required = True

    def clean(self):
        cleaned_data = super().clean()
        if self.creneau and not self.creneau.est_disponible():
            raise ValidationError("Ce créneau n'est plus disponible.")
        return cleaned_data


class GenererCreneauxForm(forms.Form):
    DATE_DEBUT_CHOICES = [
        ('today', "Aujourd'hui"),
        ('monday', "Lundi prochain"),
        ('next_month', "Début du mois prochain"),
    ]

    date_debut = forms.ChoiceField(
        choices=DATE_DEBUT_CHOICES,
        label="Commencer à partir de",
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'})
    )

    nombre_semaines = forms.IntegerField(
        min_value=1,
        max_value=12,
        initial=4,
        label="Nombre de semaines à générer",
        widget=forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'})
    )

    type_rdv = forms.ChoiceField(
        choices=CreneauRdv.TYPE_RDV_CHOICES,
        initial='PERMANENCE',
        label="Type de RDV",
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'})
    )


class JourBloqueForm(forms.ModelForm):
    class Meta:
        model = JourBloque
        fields = ['date', 'raison', 'raison_detail', 'salle', 'agent', 'heure_debut', 'heure_fin']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields['salle'].queryset = MDSReception.objects.filter(actif=True)
        self.fields['agent'].queryset = User.objects.filter(is_active=True)

        if self.request and self.request.user.a_la_capacite('peut_administrer'):
            profile = UserMDSProfile.objects.filter(
                user=self.request.user, actif=True
            ).first()
            if profile and profile.mds:
                self.fields['salle'].queryset = MDSReception.objects.filter(
                    mds=profile.mds, actif=True
                )
                self.fields['agent'].queryset = User.objects.filter(
                    profils__capacites__code='peut_creer',
                    is_active=True
                ).distinct()

    def clean(self):
        cleaned_data = super().clean()
        salle = cleaned_data.get('salle')
        agent = cleaned_data.get('agent')

        if self.request and self.request.method == 'POST':
            if not salle and not agent:
                raise ValidationError(
                    "Vous devez sélectionner au moins une salle ou un agent."
                )

        return cleaned_data
# À AJOUTER dans planning/forms.py après les autres classes parce que DeepSeek n'a pas écouté quand je lui ai dit que c'est au CADRE de faire ça et pas à l'Admin

class PermanenceExterneForm(forms.ModelForm):
    class Meta:
        model = PermanenceExterne
        fields = ['agent', 'salle', 'jour_semaine', 'heure_debut', 'heure_fin', 
                  'recurrence', 'actif', 'date_debut', 'date_fin']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border rounded-lg'}),
            'date_fin': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border rounded-lg'}),
            'heure_debut': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-3 py-2 border rounded-lg'}),
            'heure_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-3 py-2 border rounded-lg'}),
            'jour_semaine': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'recurrence': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'agent': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'salle': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and hasattr(self.user, 'mds_principale'):
            mds = self.user.mds_principale
            # Filtrer les agents de la MDS
            self.fields['agent'].queryset = User.objects.filter(
                profils_mds__mds=mds,
                profils_mds__actif=True
            ).distinct().order_by('last_name')
            # Filtrer les salles de la MDS (y compris externes)
            self.fields['salle'].queryset = MDSReception.objects.filter(
                mds=mds
            ).order_by('nom')
        
        # Labels plus clairs
        self.fields['jour_semaine'].label = "Jour de la semaine"
        self.fields['heure_debut'].label = "Heure de début"
        self.fields['heure_fin'].label = "Heure de fin"
