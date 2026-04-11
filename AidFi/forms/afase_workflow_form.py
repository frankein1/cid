# AidFi/forms/afase_workflow_form.py

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
from AidFi.models.m_generique import DemandeAide
from beneficiaire.models import Beneficiaire, LienFamilial


class AFASEWorkflowForm(forms.Form):
    """
    Formulaire métier AFASE.
    Centralise la saisie, les calculs et la validation.
    """

    # ==========================================================
    # BLOC 1 — CONTEXTE / DEMANDEUR
    # ==========================================================

    demandeur = forms.ModelChoiceField(
        queryset=Beneficiaire.objects.none(),
        label="Personne ayant formulé la demande",
    )

    numero_genesis = forms.CharField(required=False, label="N° GENESIS")
    premiere_demande = forms.BooleanField(required=False)
    avis_ts = forms.ChoiceField(
        choices=DemandeAFASE.AVIS_TS_CHOICES,
        label="Avis du travailleur social",
    )

    montant_sollicite = forms.DecimalField(min_value=0)
    duree_demande = forms.IntegerField(min_value=1)

    # ==========================================================
    # BLOC 2 — ÉVALUATION SOCIALE
    # ==========================================================

    code_instruction = forms.ChoiceField(choices=[(k, v) for k, v in CODES_INSTRUCTION_AFASE.items()],label="Code de la demande AFASE",required=True,)
    situation_sociale = forms.CharField(widget=forms.Textarea, required=False)
    analyse_problematique = forms.CharField(widget=forms.Textarea, required=False)
    justification_demande = forms.CharField(widget=forms.Textarea)
    commentaire_familial = forms.CharField(widget=forms.Textarea, required=False)

    # ==========================================================
    # BLOC 3 — BUDGET
    # ==========================================================

    ressources = forms.JSONField(required=False)
    charges = forms.JSONField(required=False)

    total_ressources = forms.DecimalField(required=False, widget=forms.HiddenInput)
    total_charges = forms.DecimalField(required=False, widget=forms.HiddenInput)
    reste_a_vivre = forms.DecimalField(required=False, widget=forms.HiddenInput)

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(self, *, beneficiaire, user, demande=None, **kwargs):
        super().__init__(**kwargs)

        self.beneficiaire = beneficiaire
        self.user = user
        self.demande = demande

        # --- Construction de la liste des demandeurs possibles
        famille_ids = {beneficiaire.id}

        liens = LienFamilial.objects.filter(
            personne_a=beneficiaire
        ) | LienFamilial.objects.filter(personne_b=beneficiaire)

        for lien in liens:
            famille_ids.add(lien.personne_a_id)
            famille_ids.add(lien.personne_b_id)

        self.fields["demandeur"].queryset = Beneficiaire.objects.filter(
            id__in=famille_ids
        )

        # --- Pré-remplissage si édition
        if demande:
            self.initial.update({
                "demandeur": demande.demandeur,
                "numero_genesis": demande.numero_genesis,
                "premiere_demande": demande.premiere_demande,
                "avis_ts": demande.avis_ts,
                "montant_sollicite": demande.montant_sollicite,
                "duree_demande": demande.duree_demande,
            })

            if hasattr(demande, "evaluation_afase"):
                eval = demande.evaluation_afase
                self.initial.update({
                    "code_instruction": eval.code_instruction,
                    "situation_sociale": eval.situation_sociale,
                    "analyse_problematique": eval.analyse_problematique,
                    "justification_demande": eval.justification_demande,
                    "commentaire_familial": eval.commentaire_familial,
                })

            if hasattr(demande, "budget"):
                budget = demande.budget
                self.initial.update({
                    "ressources": budget.ressources,
                    "charges": budget.charges,
                    "total_ressources": sum(budget.ressources.values()),
                    "total_charges": sum(budget.charges.values()),
                    "reste_a_vivre": budget.reste_a_vivre,
                })

    # ==========================================================
    # VALIDATION MÉTIER
    # ==========================================================

    def clean(self):
        cleaned = super().clean()

        ressources = cleaned.get("ressources") or {}
        charges = cleaned.get("charges") or {}

        if not isinstance(ressources, dict) or not isinstance(charges, dict):
            raise ValidationError("Ressources et charges doivent être des dictionnaires.")

        total_ressources = sum(Decimal(v or 0) for v in ressources.values())
        total_charges = sum(Decimal(v or 0) for v in charges.values())

        cleaned["total_ressources"] = total_ressources
        cleaned["total_charges"] = total_charges

    # ✅ CALCUL DU NOMBRE DE PERSONNES AU FOYER
        nb_personnes = 1  # Le bénéficiaire lui-même
    
    # Compter les membres de la famille vivant au foyer
        liens = self.beneficiaire.liens_familiaux.all()
        for lien in liens:
            if lien.vit_au_foyer:
                nb_personnes += 1

        if nb_personnes <= 0:
            nb_personnes = 1

        reste_a_vivre = (total_ressources - total_charges) / Decimal(nb_personnes) / Decimal("30")
        cleaned["reste_a_vivre"] = round(reste_a_vivre, 2)

        return cleaned

    # ==========================================================
    # SAVE TRANSACTIONNEL
    # ==========================================================

    @transaction.atomic
    def save(self):  # ✅ MAINTENANT CORRECTEMENT INDENTÉ (4 espaces)
        """
        Crée ou met à jour l'ensemble du dossier AFASE.
        """
        # Import ici pour éviter les imports circulaires
        from AidFi.models.m_generique import TypeAide
        
        if self.demande:
            demande = self.demande
        else:
            # S'assurer que le TypeAide AFASE existe
            type_aide_afase, _ = TypeAide.objects.get_or_create(
                code='AFASE',
                defaults={
                    'nom': 'Aide Financière ASE',
                    'description': 'Aide financière pour les enfants relevant de l\'ASE',
                    'actif': True,
                    'cree_par': self.user,
                }
            )
            
            demande = DemandeAFASE.objects.create(
                beneficiaire=self.beneficiaire,
                type_aide=type_aide_afase,
                demandeur=self.cleaned_data["demandeur"],
                cree_par=self.user,
                statut="BROUILLON",
            )

        # --- DemandeAFASE
        demande.demandeur = self.cleaned_data["demandeur"]
        demande.numero_genesis = self.cleaned_data["numero_genesis"]
        demande.premiere_demande = self.cleaned_data["premiere_demande"]
        demande.avis_ts = self.cleaned_data["avis_ts"]
        demande.montant_sollicite = self.cleaned_data["montant_sollicite"]
        demande.duree_demande = self.cleaned_data["duree_demande"]
        demande.save()

        # --- Évaluation sociale
        EvaluationSocialeAFASE.objects.update_or_create(
            demande=demande,
            defaults={
                "code_instruction": self.cleaned_data["code_instruction"],
                "situation_sociale": self.cleaned_data["situation_sociale"],
                "analyse_problematique": self.cleaned_data["analyse_problematique"],
                "justification_demande": self.cleaned_data["justification_demande"],
                "commentaire_familial": self.cleaned_data["commentaire_familial"],
            }
        )

        # --- Budget
        BudgetAFASE.objects.update_or_create(
            demande=demande,
            defaults={
                "ressources": self.cleaned_data["ressources"],
                "charges": self.cleaned_data["charges"],
                "reste_a_vivre": self.cleaned_data["reste_a_vivre"],
            }
        )

        return demande
