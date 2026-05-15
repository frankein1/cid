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
            "code_decision_accord",  # ← nouveau champ virtuel
            "code_decision_refus",   # ← nouveau champ virtuel
            "montant_accorde",
            "duree_accordee",
            "motivation",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Champ virtuel pour les motifs d'accord
        self.fields["code_decision_accord"] = forms.ChoiceField(
            choices=[("", "--- Sélectionner un motif d'accord ---")] + ACCORD_AFASE_CHOICES,
            required=False,
            label="Motif d'accord"
        )
        
        # Champ virtuel pour les motifs de refus
        self.fields["code_decision_refus"] = forms.ChoiceField(
            choices=[("", "--- Sélectionner un motif de refus ---")] + REFUS_AFASE_CHOICES,
            required=False,
            label="Motif de refus"
        )
        
        self.fields["code_decision_accord"].widget.attrs["class"] = "border-green-500"
        self.fields["code_decision_refus"].widget.attrs["class"] = "border-red-500"
        
        # Rendre la motivation obligatoire
        self.fields["motivation"].required = True
        self.fields["motivation"].label = "Motif (obligatoire en cas de refus)"

