# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

from django import forms

from AidFi.models.m_afase import (
    DemandeAFASE,
    EvaluationSocialeAFASE,
    BudgetAFASE,
    DecisionAFASE,
    ACCORD_AFASE_CHOICES,
    REFUS_AFASE_CHOICES,
)


class DemandeAFASEForm(forms.ModelForm):
    class Meta:
        model = DemandeAFASE
        fields = (
            "numero_genesis",
            "premiere_demande",
            "avis_ts",
            "montant_sollicite",
            "duree_demande",
        )


class EvaluationSocialeAFASEForm(forms.ModelForm):
    class Meta:
        model = EvaluationSocialeAFASE
        fields = (
            "situation_sociale",
            "analyse_problematique",
            "justification_demande",
            "commentaire_familial",
        )


class BudgetAFASEForm(forms.ModelForm):
    class Meta:
        model = BudgetAFASE
        fields = ("ressources", "charges")


class DecisionAFASEForm(forms.ModelForm):
    class Meta:
        model = DecisionAFASE
        fields = (
            "type_decision",
            "code_decision",
            "montant_accorde",
            "duree_accordee",
            "motivation",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["code_decision"].widget = forms.Select(
            choices=[("", "--- Sélectionner un motif ---"), *ACCORD_AFASE_CHOICES, *REFUS_AFASE_CHOICES]
        )
