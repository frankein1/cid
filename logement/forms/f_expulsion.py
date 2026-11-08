# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/forms/f_expulsion.py
"""Saisie d'un dossier de prévention des expulsions : les rubriques de la fiche de liaison CD13 – CAF, la décision du
tribunal et la fiche CAF « Prévention de l'expulsion domiciliaire »."""
from django import forms

from logement.models import DossierExpulsion, EtapeExpulsion
from logement.models.m_expulsion import CHAMPS_CAF, DECISION_CASES, DUREES_DELAI

CHAMP = "w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
DATE = forms.DateInput(attrs={'type': 'date', 'class': CHAMP}, format='%Y-%m-%d')


class DossierExpulsionForm(forms.ModelForm):
    class Meta:
        model = DossierExpulsion
        fields = ['origine', 'date_reception', 'mds', 'nom', 'prenom', 'colocataire', 'adresse', 'code_postal', 'ville',
                  'proprietaire', 'type_bailleur', 'date_signature_bail', 'loyer_total', 'loyer', 'charges', 'dette',
                  'dette_au', 'numero_allocataire', 'observation_caf', 'retour_le', 'association', 'ccas',
                  'tribunal', 'date_audience', 'heure_audience', 'date_decision', 'observations']
        widgets = {'date_reception': DATE, 'date_signature_bail': DATE, 'dette_au': DATE, 'retour_le': DATE,
                   'date_audience': DATE, 'date_decision': DATE,
                   'proprietaire': forms.Textarea(attrs={'rows': 3}), 'observations': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, user=None, mds_possibles=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usager = None
        self.fields['code_usager'] = forms.CharField(
            label="Code usager CID", required=False, initial=getattr(self.instance.beneficiaire, 'code_interne', ''),
            help_text="Trouvé dans l'annuaire des usagers. À défaut, CID cherche le n° allocataire parmi les usagers.")
        self.fields['nom'].required = False
        d = self.instance.decision or {}
        caf = self.instance.caf or {}
        for cle, lib in DECISION_CASES:
            self.fields[f'dec_{cle}'] = forms.BooleanField(label=lib, required=False, initial=bool(d.get(cle)))
        self.fields['dec_provisions_montant'] = forms.CharField(label="Montant des provisions", required=False,
                                                                initial=d.get('provisions_montant', ''))
        self.fields['dec_duree_delai'] = forms.ChoiceField(label="Durée du délai", required=False,
                                                           choices=[('', '—')] + DUREES_DELAI,
                                                           initial=d.get('duree_delai', ''))
        self.fields['dec_duree_autre'] = forms.CharField(label="Autre durée", required=False,
                                                         initial=d.get('duree_autre', ''))
        for cle, lib, _ in CHAMPS_CAF:
            self.fields[f'caf_{cle}'] = forms.CharField(label=lib, required=False, initial=caf.get(cle, ''),
                                                        widget=forms.Textarea(attrs={'rows': 2}) if cle == 'commentaire'
                                                        else forms.TextInput())
        if mds_possibles is not None:
            self.fields['mds'].queryset = mds_possibles
            if mds_possibles.count() == 1:
                self.fields['mds'].initial = mds_possibles.first()
                self.fields['mds'].required = True
        for nom, f in self.fields.items():
            if isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault('class', 'h-4 w-4 mr-2')
            else:
                f.widget.attrs.setdefault('class', CHAMP)

    def clean(self):
        """Code usager CID ou n° CAF → l'usager est rattaché et sa MDS proposée : pas de double saisie."""
        from beneficiaire.models import Beneficiaire
        c = super().clean()
        code = (c.get('code_usager') or '').strip().upper()
        caf = (c.get('numero_allocataire') or '').strip()
        if code:
            self.usager = Beneficiaire.objects.select_related('mds').filter(code_interne__iexact=code).first()
            if not self.usager:
                self.add_error('code_usager', "Aucun usager avec ce code : vérifiez dans l'annuaire des usagers.")
        elif caf and not self.instance.beneficiaire_id:
            trouves = list(Beneficiaire.objects.select_related('mds').filter(numero_caf=caf).exclude(statut='ARCHIVE')[:2])
            self.usager = trouves[0] if len(trouves) == 1 else None
        if self.usager:
            c['nom'] = c.get('nom') or self.usager.nom
            c['prenom'] = c.get('prenom') or self.usager.prenom
            if not c.get('mds') and self.usager.mds and self.usager.mds in self.fields['mds'].queryset:
                c['mds'] = self.usager.mds
        if not c.get('nom'):
            self.add_error('nom', "Nom obligatoire (ou code usager CID).")
        return c

    def groupes_caf(self):
        groupes = {}
        for cle, _, rub in CHAMPS_CAF:
            groupes.setdefault(rub, []).append(self[f'caf_{cle}'])
        return groupes.items()

    def champs_decision(self):
        return [self[f'dec_{cle}'] for cle, _ in DECISION_CASES]

    def save(self, commit=True):
        d = super().save(commit=False)
        c = self.cleaned_data
        d.nom, d.prenom = c['nom'], c.get('prenom') or ''
        if 'mds' in c:
            d.mds = c['mds']
        decision = {cle: True for cle, _ in DECISION_CASES if c.get(f'dec_{cle}')}
        for cle in ('provisions_montant', 'duree_delai', 'duree_autre'):
            if c.get(f'dec_{cle}'):
                decision[cle] = c[f'dec_{cle}'].strip()
        d.decision = decision
        d.caf = {cle: c[f'caf_{cle}'].strip() for cle, _, _ in CHAMPS_CAF if (c.get(f'caf_{cle}') or '').strip()}
        if commit:
            d.save()
        return d


class EtapeExpulsionForm(forms.ModelForm):
    class Meta:
        model = EtapeExpulsion
        fields = ['type_etape', 'date', 'echeance', 'commentaire']
        widgets = {'date': DATE, 'echeance': DATE, 'commentaire': forms.Textarea(attrs={'rows': 2})}
        help_texts = {'echeance': "Laissée vide, CID propose le délai habituel (commandement de payer : 6 semaines ; "
                                  "commandement de quitter les lieux : 2 mois)."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', CHAMP)

    def save(self, commit=True):
        e = super().save(commit=False)
        if not e.echeance:
            e.echeance = EtapeExpulsion.echeance_proposee(e.type_etape, e.date)
        if commit:
            e.save()
        return e
