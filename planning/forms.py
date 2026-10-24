# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

"""
planning/forms.py
VERSION FINALE AVEC RECHERCHE BÉNÉFICIAIRE
"""

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .models import CreneauRdv, JourBloque
from mds.models import MDSReception, UserMDSProfile
from beneficiaire.models import Beneficiaire

User = get_user_model()


class RdvForm(forms.ModelForm):
    # Champ de recherche pour le bénéficiaire
    beneficiaire_recherche = forms.CharField(
        label="Bénéficiaire",
        required=True,
        help_text="Tapez au moins 3 lettres (nom, prénom ou code interne)",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-md',
            'autocomplete': 'off',
            'placeholder': 'Rechercher un bénéficiaire...'
        })
    )
    beneficiaire_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = CreneauRdv
        fields = [
            'beneficiaire_id',
            'accompagnant',
            'co_intervenants',
            'domaine',
            'premiere_fois',
            'description',
            'duree_minutes'
        ]
        widgets = {
            'accompagnant': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-md'}),
            'co_intervenants': forms.SelectMultiple(attrs={'class': 'w-full px-3 py-2 border rounded-md'}),
            'domaine': forms.Select(attrs={
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

        # Si on a déjà un bénéficiaire (édition), on pré-remplit le champ recherche
        if self.instance and self.instance.beneficiaire:
            b = self.instance.beneficiaire
            self.initial['beneficiaire_recherche'] = f"{b.nom} {b.prenom} ({b.code_interne})"
            self.initial['beneficiaire_id'] = b.id

        # Rendre les champs requis
        self.fields['beneficiaire_recherche'].required = True
        self.fields['domaine'].required = True
        self.fields['description'].required = True

        # Co-intervenants : agents de la MDS
        if self.request and hasattr(self.request.user, 'mds_principale'):
            mds = self.request.user.mds_principale
            ids_agents = UserMDSProfile.objects.filter(
                mds=mds, actif=True
            ).values_list('user_id', flat=True)
            self.fields['co_intervenants'].queryset = User.objects.filter(
                id__in=ids_agents
            ).order_by('last_name')

    def clean(self):
        cleaned_data = super().clean()
        
        # Vérification que le créneau est toujours disponible
        if self.creneau and not self.creneau.is_disponible():
            raise ValidationError("Ce créneau n'est plus disponible.")
        
        # Récupération du bénéficiaire depuis l'ID caché
        beneficiaire_id = cleaned_data.get('beneficiaire_id')
        if not beneficiaire_id:
            raise ValidationError("Veuillez sélectionner un bénéficiaire valide.")
        
        try:
            beneficiaire = Beneficiaire.objects.get(id=beneficiaire_id)
        except Beneficiaire.DoesNotExist:
            raise ValidationError("Bénéficiaire introuvable.")
        
        cleaned_data['beneficiaire'] = beneficiaire
        
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
    inclure_externes = forms.BooleanField(
        required=False,
        initial=True,
        label="🏢 Inclure les salles externes (CCAS, écoles, etc.)",
        help_text="Génère aussi les créneaux des permanences externes actives"
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

        # CORE : l'administrateur voit tout ; les autres sont limités à leur MDS
        if self.request and not self.request.user.a_la_capacite('peut_administrer'):
            profile = UserMDSProfile.objects.filter(
                user=self.request.user, actif=True
            ).first()
            mds = profile.mds if profile else None
            self.fields['salle'].queryset = MDSReception.objects.filter(
                mds=mds, actif=True
            )
            self.fields['agent'].queryset = User.objects.filter(
                profils_mds__mds=mds,
                profils_mds__actif=True,
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


class PermanenceExterneForm(forms.ModelForm):
    class Meta:
        from .models import PermanenceExterne
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
            ids_agents = UserMDSProfile.objects.filter(
                mds=mds, actif=True
            ).values_list('user_id', flat=True)
            self.fields['agent'].queryset = User.objects.filter(
                id__in=ids_agents
            ).order_by('last_name')
            
            self.fields['salle'].queryset = MDSReception.objects.filter(
                mds=mds
            ).order_by('nom')
        
        self.fields['jour_semaine'].label = "Jour de la semaine"
        self.fields['heure_debut'].label = "Heure de début"
        self.fields['heure_fin'].label = "Heure de fin"


# =============================================================================
# AGENDA UNIFIÉ : rendez-vous hors permanence (VAD, hors permanence, partenaire…)
# =============================================================================

class RdvAgentForm(forms.Form):
    """
    Rendez-vous noté par un agent social ou d'accueil dans l'agenda unifié.
    Contrairement aux permanences : pas de salle, horaires libres, saisie a posteriori possible.
    """
    motif = forms.ChoiceField(label="Motif")
    agent = forms.ModelChoiceField(queryset=User.objects.none(), label="Agent")
    date = forms.DateField(label="Date", widget=forms.DateInput(attrs={'type': 'date'}))
    heure_debut = forms.TimeField(label="Début", widget=forms.TimeInput(attrs={'type': 'time'}))
    heure_fin = forms.TimeField(label="Fin", widget=forms.TimeInput(attrs={'type': 'time'}))
    beneficiaire_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    lieu_precis = forms.CharField(label="Lieu", required=False, max_length=200,
                                  help_text="Adresse de la VAD, structure du partenaire…")
    co_intervenants = forms.ModelMultipleChoiceField(queryset=User.objects.none(), required=False,
                                                     label="Co-intervenants")
    description = forms.CharField(label="Motif détaillé (visible de l'agent et du cadre)", required=False,
                                  widget=forms.Textarea(attrs={'rows': 3}))
    premiere_fois = forms.BooleanField(label="1er rendez-vous avec un agent social de la MDS", required=False)

    def __init__(self, *args, mds=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .agenda import choix_motifs
        self.mds = mds
        self.fields['motif'].choices = choix_motifs()
        agents = User.objects.filter(profils_mds__mds=mds, profils_mds__actif=True, is_active=True)\
            .distinct().order_by('last_name', 'first_name')
        self.fields['agent'].queryset = agents
        self.fields['co_intervenants'].queryset = agents
        self.fields['agent'].label_from_instance = lambda u: u.get_full_name() or u.username
        self.fields['co_intervenants'].label_from_instance = lambda u: u.get_full_name() or u.username
        for name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.HiddenInput)):
                field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md'

    def clean(self):
        data = super().clean()
        debut, fin = data.get('heure_debut'), data.get('heure_fin')
        if debut and fin and debut >= fin:
            self.add_error('heure_fin', "L'heure de fin doit être après l'heure de début.")
        nature, _, domaine = (data.get('motif') or '').partition('|')
        data['nature'], data['domaine'] = nature, domaine
        if nature == 'PARTENAIRE' and not data.get('lieu_precis'):
            self.add_error('lieu_precis', "Indiquez le lieu ou la structure du partenaire.")
        data['beneficiaire'] = None
        if data.get('beneficiaire_id'):
            data['beneficiaire'] = Beneficiaire.objects.filter(pk=data['beneficiaire_id'], mds=self.mds).first()
            if data['beneficiaire'] is None:
                self.add_error(None, "Usager introuvable dans votre MDS.")
        if nature == 'VAD' and not data.get('beneficiaire'):
            self.add_error(None, "Une visite à domicile concerne un usager : sélectionnez-le.")
        agent, date = data.get('agent'), data.get('date')
        if agent and date and debut and fin and not self.errors:
            from .agenda import conflits_agent
            conflit = conflits_agent(agent, date, debut, fin).first()
            if conflit:
                self.add_error(None, f"{agent.get_full_name() or agent.username} est déjà pris(e) de "
                                     f"{conflit.heure_debut:%H:%M} à {conflit.heure_fin:%H:%M} "
                                     f"({conflit.get_nature_display().lower()}).")
        return data


ISSUES_RDV = [
    ('VENU_RECU', "Réalisé (venu et reçu)"),
    ('VAD_ABSENT', "VAD – usager absent (déplacement effectué)"),
    ('ABSENT', "Usager absent"),
    ('VENU_NON_RECU', "Venu non reçu"),
    ('ANNULE_USAGER', "Annulé par l'usager"),
    ('REPORT_USAGER', "Reporté par l'usager"),
    ('ANNULE_MDS', "Annulé par la MDS"),
    ('REPORT_MDS', "Reporté par la MDS"),
    ('RESERVE', "Prévu (remettre à prévu)"),
]
