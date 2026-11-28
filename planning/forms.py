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
from core.horaires import TexteHoraire, TexteDateHeure, verifier_pas_de_dix
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .models import CreneauRdv, JourBloque
from mds.models import MDSReception, UserMDSProfile
from beneficiaire.models import Beneficiaire

User = get_user_model()




class SaisieHoraire:
    """Horaires saisis en 24 h (HH:MM) quel que soit l'appareil, et par pas de 10 minutes (00, 10, 20…)."""
    CHAMPS_HORAIRES = ('heure_debut', 'heure_fin')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nom in self.CHAMPS_HORAIRES:
            if nom in self.fields:
                self.fields[nom].widget = TexteHoraire(attrs={
                    'placeholder': 'HH:MM', 'pattern': r'([01]\d|2[0-3]):[0-5]\d', 'maxlength': '5',
                    'autocomplete': 'off', 'inputmode': 'numeric',
                    'class': 'w-full px-3 py-2 border rounded-lg'})
                self.fields[nom].input_formats = ['%H:%M']

    def _pas_de_dix_minutes(self, nom):
        valeur = self.cleaned_data.get(nom)
        if valeur and valeur.minute % 10:
            raise ValidationError("Les horaires se saisissent par pas de 10 minutes (00, 10, 20, 30, 40 ou 50).")
        return valeur

    def clean_heure_debut(self):
        return self._pas_de_dix_minutes('heure_debut')

    def clean_heure_fin(self):
        return self._pas_de_dix_minutes('heure_fin')


def lieu_du_rendez_vous(nature, beneficiaire, lieu_saisi):
    """Lieu enregistré pour un rendez-vous. Une VAD se fait au domicile de l'usager (adresse de la fiche) ;
    un rendez-vous hors permanence doit indiquer son lieu. Retourne (lieu, message d'erreur ou None)."""
    if nature == 'VAD':
        if beneficiaire is None or not (beneficiaire.adresse or '').strip():
            return '', "Adresse du domicile absente de la fiche : complétez-la avant la visite."
        return f"Domicile : {beneficiaire.adresse}, {beneficiaire.code_postal} {beneficiaire.ville}".strip(), None
    if nature == 'HORS_PERMANENCE' and not (lieu_saisi or '').strip():
        return '', "Indiquez le lieu du rendez-vous hors permanence (MDS, structure, autre)."
    return (lieu_saisi or '').strip(), None


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


class JourBloqueForm(SaisieHoraire, forms.ModelForm):
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


class PermanenceExterneForm(SaisieHoraire, forms.ModelForm):
    class Meta:
        from .models import PermanenceExterne
        model = PermanenceExterne
        fields = ['agent', 'salle', 'jour_semaine', 'heure_debut', 'heure_fin', 
                  'recurrence', 'actif', 'date_debut', 'date_fin']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border rounded-lg'}),
            'date_fin': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border rounded-lg'}),
            'heure_debut': TexteHoraire(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
            'heure_fin': TexteHoraire(attrs={'class': 'w-full px-3 py-2 border rounded-lg'}),
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

TYPES_LIEU = [
    ('', "Saisie libre (partenaire, structure, autre)"),
    ('DOMICILE', "Domicile de l'usager (adresse de la fiche)"),
    ('MDS', "MDS (adresse de la MDS, salle de réception réservée)"),
]


def memo_domicile(beneficiaire, precision=''):
    """Mémo de lieu : adresse de la fiche usager, précision facultative (bâtiment, étage)."""
    adresse = f"Domicile : {beneficiaire.adresse}, {beneficiaire.code_postal} {beneficiaire.ville}".strip()
    return f"{adresse} – {precision.strip()}" if (precision or '').strip() else adresse


def memo_mds(mds, salle=None):
    """Mémo de lieu : adresse de la MDS. La salle, si elle est réservée, reste un lien à part : elle n'apparaît
    pas sur les courriers."""
    return f"MDS : {mds.adresse}, {mds.code_postal} {mds.ville}".strip()


class RdvAgentForm(SaisieHoraire, forms.Form):
    """
    Rendez-vous noté par un agent social ou d'accueil dans l'agenda unifié.
    Contrairement aux permanences : pas de salle, horaires libres, saisie a posteriori possible.
    """
    motif = forms.ChoiceField(label="Motif")
    agent = forms.ModelChoiceField(queryset=User.objects.none(), label="Agent")
    date = forms.DateField(label="Date", widget=forms.DateInput(attrs={'type': 'date'}))
    heure_debut = forms.TimeField(label="Début", widget=TexteHoraire())
    heure_fin = forms.TimeField(label="Fin", widget=TexteHoraire())
    beneficiaire_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    lieu_type = forms.ChoiceField(label="Lieu", choices=TYPES_LIEU, required=False, initial='')
    lieu_precision = forms.CharField(label="Précision du domicile", required=False, max_length=120,
                                     help_text="Bâtiment, étage… (facultatif)")
    lieu_precis = forms.CharField(label="Lieu (saisie libre)", required=False, max_length=200,
                                  help_text="Structure du partenaire, autre lieu…")
    salle = forms.ModelChoiceField(queryset=None, required=False, label="Salle de réception",
                                   help_text="Réserve la salle sur l'horaire, marge de 30 min comprise.")
    co_intervenants = forms.ModelMultipleChoiceField(queryset=User.objects.none(), required=False,
                                                     label="Co-intervenants")
    partenaires = forms.ModelMultipleChoiceField(queryset=None, required=False, label="Partenaires",
                                                 help_text="Annuaire commun aux MDS. Rendez-vous tripartite : "
                                                           "usager + partenaire.")
    description = forms.CharField(label="Motif détaillé (visible de l'agent et du cadre)", required=False,
                                  widget=forms.Textarea(attrs={'rows': 3}))
    premiere_fois = forms.BooleanField(label="1er rendez-vous avec un agent social de la MDS", required=False)

    def __init__(self, *args, mds=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .agenda import choix_motifs
        self.mds = mds
        self.fields['motif'].choices = choix_motifs()
        from partenaires.models import Partenaire
        self.fields['partenaires'].queryset = Partenaire.objects.filter(actif=True)
        from mds.models import MDSReception
        self.fields['salle'].queryset = MDSReception.objects.filter(mds=mds, actif=True) if mds else MDSReception.objects.none()
        self.fields['salle'].label_from_instance = lambda s: s.nom
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
        if nature == 'PARTENAIRE' and not data.get('lieu_precis') and not data.get('partenaires'):
            self.add_error('partenaires', "Choisissez le partenaire (ou indiquez au moins le lieu).")
        data['beneficiaire'] = None
        if data.get('beneficiaire_id'):
            data['beneficiaire'] = Beneficiaire.objects.filter(pk=data['beneficiaire_id'], mds=self.mds).first()
            if data['beneficiaire'] is None:
                self.add_error(None, "Usager introuvable dans votre MDS.")
        if nature == 'VAD' and not data.get('beneficiaire'):
            self.add_error(None, "Une visite à domicile concerne un usager : sélectionnez-le.")
        type_lieu = data.get('lieu_type') or ('DOMICILE' if nature == 'VAD' else '')
        erreur = None
        if type_lieu == 'DOMICILE':
            if not data.get('beneficiaire') or not (data['beneficiaire'].adresse or '').strip():
                erreur = "Adresse du domicile absente de la fiche : complétez-la avant la visite."
                lieu = ''
            else:
                lieu = memo_domicile(data['beneficiaire'], data.get('lieu_precision'))
        elif type_lieu == 'MDS':
            lieu = memo_mds(self.mds, data.get('salle'))
        else:
            lieu, erreur = lieu_du_rendez_vous(nature, data.get('beneficiaire'), data.get('lieu_precis'))
        if erreur:
            self.add_error(None, erreur)
        data['lieu_precis'] = lieu
        # Heures d'ouverture : uniquement quand le lieu est la MDS. Hors de ces heures, il faut un autre lieu
        # (domicile, tiers lieu comme une maison des associations).
        if debut and fin and debut < fin and lieu.startswith('MDS :'):
            from .agenda import dans_heures_ouverture
            if not dans_heures_ouverture(debut, fin):
                self.add_error(None, "À la MDS, les rendez-vous se prennent aux heures d'ouverture : 9 h - 12 h "
                                     "ou 13 h 30 - 17 h. Pour un autre horaire, indiquez un autre lieu "
                                     "(domicile, tiers lieu).")
        agent, date = data.get('agent'), data.get('date')
        if agent and date and debut and fin and not self.errors:
            from .agenda import conflits_agent, salle_occupee
            conflit = conflits_agent(agent, date, debut, fin).first()
            if conflit:
                self.add_error(None, f"{agent.get_full_name() or agent.username} est déjà pris(e) de "
                                     f"{conflit.heure_debut:%H:%M} à {conflit.heure_fin:%H:%M} "
                                     f"({conflit.get_nature_display().lower()}).")
            salle = data.get('salle')
            if salle and not conflit:
                occupations = salle_occupee(salle, date, debut, fin, nature)
                if occupations:
                    autre = occupations[0]
                    self.add_error('salle', f"{salle.nom} est réservée de {autre.heure_debut:%H:%M} à "
                                            f"{autre.heure_fin:%H:%M} ({autre.get_nature_display().lower()}). "
                                            f"Choisissez une autre salle ou un autre horaire.")
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


# =============================================================================
# RÉUNIONS (lot 2) : convocation par le cadre ou l'agent administratif
# =============================================================================

class ReunionForm(SaisieHoraire, forms.Form):
    intitule = forms.CharField(label="Intitulé", max_length=120,
                               help_text="Visible des seuls participants. Ex. : Synthèse IP, réunion d'équipe…")
    domaine = forms.ChoiceField(label="Domaine", initial='INSTITUTIONNEL')
    date = forms.DateField(label="Date", widget=forms.DateInput(attrs={'type': 'date'}))
    heure_debut = forms.TimeField(label="Début", widget=TexteHoraire())
    heure_fin = forms.TimeField(label="Fin", widget=TexteHoraire())
    lieu_precis = forms.CharField(label="Lieu", max_length=200, required=False, initial="Salle de réunion")
    ordre_du_jour = forms.CharField(label="Ordre du jour", required=False, widget=forms.Textarea(attrs={'rows': 3}))
    participants = forms.ModelMultipleChoiceField(queryset=User.objects.none(), label="Participants",
                                                  widget=forms.CheckboxSelectMultiple)
    # Dossier concerné (ex. synthèse IP) : la réunion apparaît alors sur la fiche de l'usager
    beneficiaire_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, mds=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.mds = mds
        from .models import DOMAINES_RDV
        self.fields['domaine'].choices = DOMAINES_RDV
        self.fields['participants'].queryset = User.objects.filter(
            profils_mds__mds=mds, profils_mds__actif=True, is_active=True).distinct().order_by('last_name', 'first_name')
        for name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxSelectMultiple, forms.CheckboxInput)):
                field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md'

    def clean(self):
        data = super().clean()
        debut, fin, jour = data.get('heure_debut'), data.get('heure_fin'), data.get('date')
        if debut and fin and debut >= fin:
            self.add_error('heure_fin', "L'heure de fin doit être après l'heure de début.")
        from django.utils import timezone
        if jour and jour < timezone.localdate():
            self.add_error('date', "Une réunion se convoque pour aujourd'hui ou plus tard.")
        data['beneficiaire'] = None
        if data.get('beneficiaire_id'):
            data['beneficiaire'] = Beneficiaire.objects.filter(pk=data['beneficiaire_id'], mds=self.mds).first()
            if data['beneficiaire'] is None:
                self.add_error(None, "Dossier introuvable dans votre MDS.")
        return data
