from django import forms
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal

from AidFi.models.m_afase import (
    DemandeAFASE,
    EvaluationSocialeAFASE,
    BudgetAFASE,
    CODES_INSTRUCTION_AFASE,
)
from AidFi.models.m_generique import TypeAide
from beneficiaire.models import Beneficiaire, LienFamilial


class AFASEWorkflowForm(forms.Form):
    demandeur = forms.ModelChoiceField(queryset=Beneficiaire.objects.none(), label="Personne ayant formulé la demande")
    numero_genesis = forms.CharField(max_length=50, required=False, label="Numéro GENESIS")
    premiere_demande = forms.BooleanField(required=False)
    avis_ts = forms.ChoiceField(choices=DemandeAFASE.AVIS_TS_CHOICES, label="Avis du travailleur social")
    montant_sollicite = forms.DecimalField(min_value=0)
    duree_demande = forms.IntegerField(min_value=1)
    code_instruction = forms.ChoiceField(choices=[(k, v) for k, v in CODES_INSTRUCTION_AFASE.items()], label="Code de la demande AFASE", required=True,)
    situation_sociale = forms.CharField(widget=forms.Textarea, required=False)
    analyse_problematique = forms.CharField(widget=forms.Textarea, required=False)
    justification_demande = forms.CharField(widget=forms.Textarea)
    commentaire_familial = forms.CharField(widget=forms.Textarea, required=False)

    documents_ged = forms.ModelMultipleChoiceField(queryset=DocumentGED.objects.none(), required=False, widget=forms.CheckboxSelectMultiple, label="Documents GED à joindre à la demande")
    
    ressources = forms.JSONField(required=False)
    charges = forms.JSONField(required=False)

    total_ressources = forms.DecimalField(required=False, widget=forms.HiddenInput)
    total_charges = forms.DecimalField(required=False, widget=forms.HiddenInput)
    reste_a_vivre = forms.DecimalField(required=False, widget=forms.HiddenInput)

    def __init__(self, *, beneficiaire, user, demande=None, **kwargs):
        super().__init__(**kwargs)
        self.beneficiaire = beneficiaire
        self.user = user
        self.demande = demande
        
        
        famille_ids = {beneficiaire.id}
        liens = LienFamilial.objects.filter(personne_a=beneficiaire) | LienFamilial.objects.filter(personne_b=beneficiaire)
        for lien in liens:
            famille_ids.add(lien.personne_a_id)
            famille_ids.add(lien.personne_b_id)

        self.fields["demandeur"].queryset = Beneficiaire.objects.filter(id__in=famille_ids)
        if beneficiaire: self.fields['documents_ged'].queryset = DocumentGED.objects.filter(content_type=ContentType.objects.get_for_model(beneficiaire), object_id=beneficiaire.id)

        if demande:
            self.initial.update({
                "demandeur": getattr(demande, "demandeur", None),
                "numero_genesis": demande.numero_genesis,
                "premiere_demande": demande.premiere_demande,
                "avis_ts": demande.avis_ts,
                "montant_sollicite": demande.montant_sollicite,
                "duree_demande": demande.duree_demande,
            })
            if hasattr(demande, "evaluation_afase"):
                eval_obj = demande.evaluation_afase
                self.initial.update({
                    "code_instruction": eval_obj.code_instruction,
                    "situation_sociale": eval_obj.situation_sociale,
                    "analyse_problematique": eval_obj.analyse_problematique,
                    "justification_demande": eval_obj.justification_demande,
                    "commentaire_familial": eval_obj.commentaire_familial,
                })
            if hasattr(demande, "budget"):
                budget = demande.budget
                self.initial.update({
                    "ressources": budget.ressources,
                    "charges": budget.charges,
                    "total_ressources": sum(budget.ressources.values()) if budget.ressources else 0,
                    "total_charges": sum(budget.charges.values()) if budget.charges else 0,
                    "reste_a_vivre": budget.reste_a_vivre,
                })
        else:
            if beneficiaire.numero_genesis:
                self.initial["numero_genesis"] = beneficiaire.numero_genesis

    def clean(self):
        cleaned = super().clean()

        ressources = cleaned.get("ressources") or {}
        charges = cleaned.get("charges") or {}

        if not isinstance(ressources, dict) or not isinstance(charges, dict):
            raise ValidationError("Ressources et charges doivent être des dictionnaires.")

        total_ressources = sum(Decimal(str(v) or 0) for v in ressources.values())
        total_charges = sum(Decimal(str(v) or 0) for v in charges.values())

        cleaned["total_ressources"] = total_ressources
        cleaned["total_charges"] = total_charges

        nb_personnes = 1
        for lien in self.beneficiaire.liens_familiaux.all():
            if lien.vit_au_foyer:
                nb_personnes += 1

        reste_a_vivre = (total_ressources - total_charges) / Decimal(nb_personnes) / Decimal("30")
        cleaned["reste_a_vivre"] = round(reste_a_vivre, 2)
        return cleaned

    @transaction.atomic
    def save(self):
        numero_genesis = self.cleaned_data.get("numero_genesis")
        if numero_genesis and self.beneficiaire.numero_genesis != numero_genesis:
            self.beneficiaire.numero_genesis = numero_genesis
            self.beneficiaire.save(update_fields=["numero_genesis"])

        if self.demande:
            demande = self.demande
        else:
            type_aide_afase, _ = TypeAide.objects.get_or_create(
                code="AFASE",
                defaults={
                    "nom": "Aide Financière ASE",
                    "description": "Aide financière pour les enfants relevant de l'ASE",
                    "actif": True,
                    "cree_par": self.user,
                },
            )
            demande = DemandeAFASE.objects.create(
                beneficiaire=self.beneficiaire,
                type_aide=type_aide_afase,
                demandeur=self.cleaned_data["demandeur"],
                cree_par=self.user,
                statut="BROUILLON",
            )

        demande.demandeur = self.cleaned_data["demandeur"]
        demande.numero_genesis = self.cleaned_data["numero_genesis"]
        demande.premiere_demande = self.cleaned_data["premiere_demande"]
        demande.avis_ts = self.cleaned_data["avis_ts"]
        demande.montant_sollicite = self.cleaned_data["montant_sollicite"]
        demande.duree_demande = self.cleaned_data["duree_demande"]
        demande.save()

        EvaluationSocialeAFASE.objects.update_or_create(
            demande=demande,
            defaults={
                "code_instruction": self.cleaned_data["code_instruction"],
                "situation_sociale": self.cleaned_data["situation_sociale"],
                "analyse_problematique": self.cleaned_data["analyse_problematique"],
                "justification_demande": self.cleaned_data["justification_demande"],
                "commentaire_familial": self.cleaned_data["commentaire_familial"],
            },
        )

        BudgetAFASE.objects.update_or_create(
            demande=demande,
            defaults={
                "ressources": self.cleaned_data["ressources"],
                "charges": self.cleaned_data["charges"],
                "reste_a_vivre": self.cleaned_data["reste_a_vivre"],
            },
        )

        return demande

    # Liaison des documents GED à la demande AFASE (via PieceJustificative)
for doc in self.cleaned_data.get('documents_ged', []):
    PieceJustificative.objects.get_or_create(
        demande=demande,
        document_ged=doc,
        defaults={
            'type_piece': 'AUTRE',
            'statut': 'VALIDE'
        }
    )
