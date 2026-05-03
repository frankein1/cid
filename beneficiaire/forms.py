"""
# beneficiaire/forms.py - VERSION CORRIGÉE
"""

from django import forms
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Beneficiaire, LienFamilial
from .fields import (
    TelephoneField, 
    DateSimplifieeField, 
    TelephoneWidget, 
    DateSimplifieeWidget
)

User = get_user_model()

class BeneficiaireForm(forms.ModelForm):
    telephone_mobile = TelephoneField(
        label="Téléphone mobile",
        widget=TelephoneWidget(),
        required=False,
    )
    telephone_fixe = TelephoneField(
        label="Téléphone fixe",
        widget=TelephoneWidget(),
        required=False,
    )
    date_naissance = DateSimplifieeField(
        label="Date de naissance",
        widget=DateSimplifieeWidget(),
    )
    date_entree = DateSimplifieeField(
        label="Date d'entrée",
        widget=DateSimplifieeWidget(),
        required=False,
    )

    class Meta:
        model = Beneficiaire
        exclude = [
            "code_interne", "date_creation", "date_modification", 
            "cree_par", "statut", "est_decede", "date_deces", 
            "date_sortie", "motif_sortie", "detail_sortie",
        ]
        widgets = {
            "adresse": forms.Textarea(attrs={"rows": 2}),
            "mds": forms.Select(),
            "referent_mds": forms.Select(),
            # ✅ CORRECTION : Virgule unique et placement correct
            'numero_genesis': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: G123456'
            }),
        }

    def __init__(self, *args, **kwargs):
        est_ayant_droit = kwargs.pop('est_ayant_droit', False)
        super().__init__(*args, **kwargs)

        if est_ayant_droit:
            if 'mds' in self.fields:
                self.fields['mds'].label = "MDS de la famille"

        # Application du style Tailwind
        for name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                c = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{c} w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500".strip()

        # Filtrage dynamique des référents si la MDS est connue
        if self.instance and hasattr(self.instance, 'mds') and self.instance.mds:
            self.fields["referent_mds"].queryset = User.objects.filter(mds_principale=self.instance.mds)

    def clean_date_naissance(self):
        date = self.cleaned_data.get('date_naissance')
        if date and date > timezone.now().date():
            raise forms.ValidationError("La date de naissance ne peut pas être dans le futur.")
        return date

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk: 
            instance.statut = 'ACTIF'
        if commit:
            instance.save()
        return instance

class SortieBeneficiaireForm(forms.ModelForm):
    date_sortie = DateSimplifieeField(label="Date de sortie", required=True)

    class Meta:
        model = Beneficiaire
        fields = ["date_sortie", "motif_sortie", "detail_sortie"]

class DecesBeneficiaireForm(forms.ModelForm):
    date_deces = DateSimplifieeField(label="Date de décès", required=True)

    class Meta:
        model = Beneficiaire
        fields = ["date_deces", "detail_sortie"]

    def save(self, commit=True):
        beneficiaire = super().save(commit=False)
        beneficiaire.est_decede = True
        beneficiaire.statut = "DECEDE"
        beneficiaire.date_sortie = beneficiaire.date_deces
        beneficiaire.motif_sortie = "DECES"
        if commit:
            beneficiaire.save()
        return beneficiaire

class LienFamilialForm(forms.ModelForm):
    class Meta:
        model = LienFamilial
        fields = ['type_lien', 'vit_au_foyer', 'est_responsable_legal', 'commentaire']
