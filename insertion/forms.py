# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/forms.py
from django import forms

from django.db.models import Q
from django.forms import inlineformset_factory

from insertion.models import (FREINS, ActionInsertion, ContratInsertion, LigneActionContrat, ParametresRSA,
                              PoleInsertion, PrescriptionInsertion, QuestionAction, TypeActionInsertion)

CHAMP = "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"


class ActionInsertionForm(forms.ModelForm):
    class Meta:
        model = ActionInsertion
        fields = ['code', 'libelle', 'type_action', 'niveau', 'mds', 'poles', 'territoire', 'porteur', 'partenaire',
                  'public_vise', 'description', 'duree', 'destinataires', 'pieces_a_joindre', 'comite_suivi',
                  'rythme_comite', 'aussi_logement', 'validation_pole', 'fiche_avec_nir', 'actif']
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


def _styler(form):
    for champ in form.fields.values():
        if not isinstance(champ.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
            champ.widget.attrs.setdefault('class', CHAMP)


DATE = forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')

# Rubriques du formulaire (titre, champs), dans l'ordre de l'imprimé
RUBRIQUES_CONTRAT = [
    ("Le contrat", ['type_contrat', 'nature', 'date_etablissement', 'duree_proposee_mois', 'heures_activite_hebdo']),
    ("Conjoint", ['conjoint_situation', 'conjoint_operateur', 'conjoint_referent']),
    ("Diagnostic : emploi et formation", ['inscrit_france_travail', 'identifiant_france_travail', 'niveau_etudes',
                                          'formation', 'experience', 'dernier_emploi', 'dernier_emploi_annee',
                                          'dernier_emploi_duree', 'emploi_recherche']),
    ("Diagnostic : langue, mobilité, santé, logement", ['francais_parle', 'francais_lu', 'francais_ecrit', 'permis_b',
                                                        'autres_permis', 'vehicule', 'couverture_base',
                                                        'couverture_complementaire', 'logement', 'logement_precision']),
    ("Incidence financière", ['incidence_creation_activite', 'incidence_formation', 'incidence_frais_annexes']),
    ("La parole du bénéficiaire", ['parole_situation', 'parole_deja_fait', 'parole_souhaits']),
    ("Le référent", ['objectifs', 'etapes', 'observations']),
    ("Aide aux transports", ['aide_transport_urbain', 'aide_transport_interurbain']),
    ("Contrat santé : certificat médical", ['certificat_mode', 'certificat_demande_le']),
    ("Signature", ['date_signature', 'engagement_renouvellement', 'accord_allocataire']),
]


class ContratForm(forms.ModelForm):
    class Meta:
        model = ContratInsertion
        fields = [c for _, champs in RUBRIQUES_CONTRAT for c in champs]
        widgets = {
            'date_etablissement': DATE, 'date_signature': DATE, 'certificat_demande_le': DATE,
            'experience': forms.Textarea(attrs={'rows': 2}), 'parole_situation': forms.Textarea(attrs={'rows': 3}),
            'parole_deja_fait': forms.Textarea(attrs={'rows': 3}), 'parole_souhaits': forms.Textarea(attrs={'rows': 3}),
            'objectifs': forms.Textarea(attrs={'rows': 3}), 'etapes': forms.Textarea(attrs={'rows': 3}),
            'observations': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parametres = ParametresRSA.courant()
        self.fields['heures_activite_hebdo'].help_text = (
            f"Au moins {self.parametres.heures_hebdo_min} h par semaine (contrat d'engagement sur mesure).")
        self.fields['duree_proposee_mois'].help_text = f"De 1 à {self.parametres.duree_max_mois} mois."
        self.fields['certificat_mode'].help_text = (
            f"Contrat santé d'une personne de moins de {self.parametres.age_limite_certificat} ans : le médecin "
            "traitant adresse un certificat au médecin du pôle. CID n'en garde aucun contenu.")
        _styler(self)

    def clean_duree_proposee_mois(self):
        d = self.cleaned_data['duree_proposee_mois']
        if not 1 <= d <= self.parametres.duree_max_mois:
            raise forms.ValidationError(f"De 1 à {self.parametres.duree_max_mois} mois.")
        return d

    def clean_heures_activite_hebdo(self):
        h = self.cleaned_data['heures_activite_hebdo']
        if h < self.parametres.heures_hebdo_min:
            raise forms.ValidationError(f"Au moins {self.parametres.heures_hebdo_min} heures par semaine.")
        return h

    def rubriques(self):
        return [(titre, [self[c] for c in champs]) for titre, champs in RUBRIQUES_CONTRAT]


class LigneActionForm(forms.ModelForm):
    class Meta:
        model = LigneActionContrat
        fields = ['action', 'libelle', 'date_entree', 'date_sortie', 'motif_sortie']
        widgets = {'date_entree': DATE, 'date_sortie': DATE}

    def __init__(self, *args, actions=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = actions if actions is not None else ActionInsertion.objects.filter(actif=True)
        if self.instance.action_id:   # une action désactivée depuis reste affichée sur le contrat
            qs = ActionInsertion.objects.filter(Q(pk__in=qs.values('pk')) | Q(pk=self.instance.action_id))
        self.fields['action'].queryset = qs
        self.fields['action'].required = False
        _styler(self)

    def clean(self):
        d = super().clean()
        if self.has_changed() and not d.get('action') and not (d.get('libelle') or '').strip() and not d.get('DELETE'):
            raise forms.ValidationError("Choisissez une action du référentiel ou décrivez la démarche.")
        return d


class _LignesBase(forms.BaseInlineFormSet):
    def __init__(self, *args, actions=None, **kwargs):
        self.actions = actions
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kw = super().get_form_kwargs(index)
        kw['actions'] = self.actions
        return kw


LignesFormSet = inlineformset_factory(ContratInsertion, LigneActionContrat, form=LigneActionForm, formset=_LignesBase,
                                      extra=2, can_delete=True)


class ReceptionForm(forms.Form):
    date_reception = forms.DateField(label="Reçu le", widget=DATE)


class AvisForm(forms.Form):
    certificat_recu_le = forms.DateField(label="Certificat reçu le", widget=DATE)
    avis = forms.ChoiceField(label="Avis", choices=ContratInsertion.AVIS, widget=forms.RadioSelect)
    motivation = forms.CharField(label="Motivation", required=False, widget=forms.Textarea(attrs={'rows': 3}),
                                 help_text="Sans aucun détail médical (pas de diagnostic, pas de traitement).")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _styler(self)


class DecisionForm(forms.Form):
    decision = forms.ChoiceField(label="Décision", choices=ContratInsertion.DECISIONS, widget=forms.RadioSelect)
    date_decision = forms.DateField(label="Commission du", widget=DATE)
    date_debut = forms.DateField(label="Contrat validé du", required=False, widget=DATE)
    duree_mois = forms.IntegerField(label="Durée validée (mois)", required=False, min_value=1)
    motif = forms.CharField(label="Motif (ajournement, non-validation)", required=False,
                            widget=forms.Textarea(attrs={'rows': 2}))
    decision_transport = forms.ChoiceField(label="Aide aux transports", required=False,
                                           choices=ContratInsertion.DECISIONS_TRANSPORT)
    motif_transport = forms.ChoiceField(label="Motif", required=False, choices=ContratInsertion.MOTIFS_TRANSPORT)
    commentaire = forms.CharField(label="Commentaires de la commission", required=False,
                                  widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _styler(self)



# =============================================================================
# Prescriptions
# =============================================================================
class PrescriptionForm(forms.ModelForm):
    """Tronc commun, freins, pièces fournies et questions propres à l'action (champs « q_<pk> »)."""
    freins = forms.MultipleChoiceField(label="Freins", choices=FREINS, required=False,
                                       widget=forms.CheckboxSelectMultiple)
    pieces_fournies = forms.MultipleChoiceField(label="Pièces fournies", required=False,
                                                widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = PrescriptionInsertion
        fields = ['situation_rsa', 'qpv', 'rqth', 'inscrit_france_travail', 'identifiant_france_travail',
                  'qualification', 'inactivite', 'freins', 'diagnostic', 'avis_motive', 'objectifs', 'demande_par',
                  'pieces_fournies', 'consentement', 'date_signature']
        widgets = {'diagnostic': forms.Textarea(attrs={'rows': 3}), 'avis_motive': forms.Textarea(attrs={'rows': 3}),
                   'objectifs': forms.Textarea(attrs={'rows': 3}), 'date_signature': DATE,
                   'demande_par': forms.RadioSelect}

    def __init__(self, *args, voit_restreintes=True, **kwargs):
        super().__init__(*args, **kwargs)
        p = self.instance
        self.fields['pieces_fournies'].choices = [(x, x) for x in p.action.liste_pieces]
        reponses = {r.question_id: r.valeur for r in p.reponses.all()}
        self.questions = []
        for q in p.action.questions.all():
            if q.restreinte and not voit_restreintes:
                continue
            nom = f"q_{q.pk}"
            valeur = reponses.get(q.pk, "")
            if q.type_reponse == q.OUI_NON:
                champ = forms.ChoiceField(choices=[('', "—"), ('oui', "Oui"), ('non', "Non")])
            elif q.type_reponse == q.CHOIX:
                champ = forms.ChoiceField(choices=[('', "—")] + [(c, c) for c in q.liste_choix])
            elif q.type_reponse == q.CHOIX_MULTIPLE:
                champ = forms.MultipleChoiceField(choices=[(c, c) for c in q.liste_choix],
                                                  widget=forms.CheckboxSelectMultiple)
                valeur = [v for v in valeur.split("\n") if v]
            elif q.type_reponse == q.DATE:
                champ = forms.DateField(widget=DATE)
            elif q.type_reponse == q.NOMBRE:
                champ = forms.DecimalField()
            else:
                champ = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}))
            champ.label, champ.help_text, champ.required = q.libelle, q.aide, False   # obligatoire : contrôlé à l'envoi
            champ.initial = valeur
            self.fields[nom] = champ
            self.questions.append((q, nom))
        _styler(self)

    def reponses(self):
        """{question_pk: texte} à enregistrer."""
        out = {}
        for q, nom in self.questions:
            v = self.cleaned_data.get(nom)
            if isinstance(v, (list, tuple)):
                v = "\n".join(v)
            elif v is None:
                v = ""
            elif hasattr(v, 'strftime'):
                v = v.strftime('%Y-%m-%d')
            out[q.pk] = str(v)
        return out

    def champs_questions(self):
        return [(q, self[nom]) for q, nom in self.questions]


class ValidationPrescriptionForm(forms.Form):
    decision = forms.ChoiceField(choices=[('valider', "Valider : adresser au porteur"), ('refuser', "Refuser")],
                                 widget=forms.RadioSelect, label="Décision du pôle")
    motif = forms.CharField(label="Motif du refus", required=False, widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _styler(self)


class RetourPorteurForm(forms.Form):
    issue = forms.ChoiceField(label="Où en est la personne ?", required=False, widget=forms.RadioSelect)
    premier_rdv_le = forms.DateField(label="Premier rendez-vous le", required=False, widget=DATE)
    premier_rdv_issue = forms.ChoiceField(label="Premier rendez-vous", required=False,
                                          choices=PrescriptionInsertion.ISSUES_RDV)
    diagnostic_finalise = forms.BooleanField(label="Diagnostic finalisé par le porteur", required=False)
    date_entree = forms.DateField(label="Entrée dans l'action le", required=False, widget=DATE)
    motif_non_integration = forms.CharField(label="Motif de non-intégration", required=False)
    date_sortie = forms.DateField(label="Sortie le", required=False, widget=DATE)
    motif_sortie = forms.CharField(label="Motif de sortie", required=False)
    reorientation = forms.ChoiceField(label="Réorientation vers", required=False,
                                      choices=PrescriptionInsertion.REORIENTATIONS)
    reorientation_precision = forms.CharField(label="Précision", required=False)
    commentaire_porteur = forms.CharField(label="Commentaire du porteur", required=False,
                                          widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, prescription=None, **kwargs):
        super().__init__(*args, **kwargs)
        P = PrescriptionInsertion
        if prescription is not None and prescription.statut == P.INTEGREE:
            choix = [('', "Toujours en cours"), (P.TERMINEE, "Terminée"), (P.ARRETEE, "Arrêtée"),
                     (P.REORIENTEE, "Réorientée")]
        else:
            choix = [('', "Pas encore de décision"), (P.INTEGREE, "Intégrée"), (P.NON_INTEGREE, "Non intégrée"),
                     (P.REORIENTEE, "Réorientée")]
        self.fields['issue'].choices = choix
        _styler(self)


QuestionsFormSet = forms.inlineformset_factory(
    ActionInsertion, QuestionAction, fields=['libelle', 'type_reponse', 'choix', 'aide', 'obligatoire', 'restreinte', 'ordre'],
    widgets={"choix": forms.Textarea(attrs={"rows": 2, "class": CHAMP}), 'libelle': forms.TextInput(attrs={'class': CHAMP}),
             'aide': forms.TextInput(attrs={'class': CHAMP}), 'type_reponse': forms.Select(attrs={'class': CHAMP}),
             'ordre': forms.NumberInput(attrs={'class': CHAMP})},
    extra=2, can_delete=True)
