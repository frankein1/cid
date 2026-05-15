# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

from django import forms
from django.core.exceptions import ValidationError

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
            "code_decision",      # ← champ réel du modèle
            "montant_accorde",
            "duree_accordee",
            "motivation",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Champ virtuel pour les motifs d'accord (N'EXISTE PAS dans le modèle)
        self.fields["code_decision_accord"] = forms.ChoiceField(
            choices=[("", "--- Sélectionner un motif d'accord ---")] + ACCORD_AFASE_CHOICES,
            required=False,
            label="Motif d'accord"
        )
        
        # Champ virtuel pour les motifs de refus (N'EXISTE PAS dans le modèle)
        self.fields["code_decision_refus"] = forms.ChoiceField(
            choices=[("", "--- Sélectionner un motif de refus ---")] + REFUS_AFASE_CHOICES,
            required=False,
            label="Motif de refus"
        )
        
        # Style CSS
        self.fields["code_decision_accord"].widget.attrs["class"] = "border-green-500 w-full p-2 rounded"
        self.fields["code_decision_refus"].widget.attrs["class"] = "border-red-500 w-full p-2 rounded"
        
        # Rendre la motivation obligatoire
        self.fields["motivation"].required = True
        self.fields["motivation"].label = "Motif (obligatoire en cas de refus)"
        
        # Cacher le champ réel code_decision (il sera rempli automatiquement)
        self.fields["code_decision"].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        type_decision = cleaned_data.get("type_decision")
        code_decision_accord = cleaned_data.get("code_decision_accord")
        code_decision_refus = cleaned_data.get("code_decision_refus")
        motivation = cleaned_data.get("motivation")
        
        # Selon le type de décision, on assigne le bon code
        if type_decision == "ACCORD":
            if not code_decision_accord:
                self.add_error("code_decision_accord", "Veuillez sélectionner un motif d'accord.")
            cleaned_data["code_decision"] = code_decision_accord
            
        elif type_decision == "REFUS":
            if not code_decision_refus:
                self.add_error("code_decision_refus", "Veuillez sélectionner un motif de refus.")
            if not motivation:
                self.add_error("motivation", "Le motif de refus est obligatoire.")
            cleaned_data["code_decision"] = code_decision_refus
        
        return cleaned_data
