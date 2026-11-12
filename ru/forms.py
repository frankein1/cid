# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from mds.models import MDS, UserMDSProfile
from .models import DemandeRelationUsager, FicheRetourSAS


STYLE = "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
User = get_user_model()


def _style_fields(form):
    for field in form.fields.values():
        field.widget.attrs["class"] = "h-4 w-4 rounded border-gray-300 text-blue-600" if isinstance(field.widget, forms.CheckboxInput) else STYLE


class DemandeRUForm(forms.ModelForm):
    class Meta:
        model = DemandeRelationUsager
        fields = [
            "canal", "priorite", "circuit", "date_reception",
            "date_cloture_souhaitee", "mds", "reference_sap", "emetteur", "reference_externe",
            "nom_usager", "prenom_usager", "adresse_usager", "coordonnees_usager", "objet",
            "resume_demande", "situation_familiale", "nombre_enfants", "revenu_principal", "age_usager",
            "usager_informe_transmission", "date_information_usager", "accompagnement_autre_service",
            "usager_informe_liaison",
        ]
        widgets = {
            "date_reception": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_cloture_souhaitee": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_information_usager": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "adresse_usager": forms.Textarea(attrs={"rows": 2}),
            "resume_demande": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "usager_informe_transmission": "À renseigner lorsque des éléments sur la situation de l'usager sont transmis.",
            "date_cloture_souhaitee": "À renseigner si une échéance particulière de clôture est indiquée.",
        }

    def __init__(self, *args, user, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        self.user = user
        self.gestionnaire_sas = user.is_superuser or user.a_la_capacite("ru_gerer_sas")
        if not self.gestionnaire_sas:
            self.fields["circuit"].choices = [(DemandeRelationUsager.Circuit.MDS, "Évaluation par ma MDS")]
            self.fields["circuit"].initial = DemandeRelationUsager.Circuit.MDS
            self.fields["mds"].queryset = MDS.objects.filter(
                id__in=UserMDSProfile.objects.filter(user=user, actif=True).values_list("mds_id", flat=True)
            ).order_by("nom")
            self.fields["mds"].required = True
            if not instance:
                self.fields["mds"].initial = self.fields["mds"].queryset.first()
        else:
            self.fields["mds"].queryset = MDS.objects.filter(active=True).order_by("nom")
        _style_fields(self)
        if not self.instance.pk:
            self.initial.setdefault("date_reception", timezone.localdate())
        if self.instance.pk:
            for name in ("circuit", "date_reception", "reference_sap"):
                if name in self.fields:
                    self.fields[name].disabled = True
            if not (self.gestionnaire_sas and self.instance.statut == DemandeRelationUsager.Statut.A_TRAITER_SAS):
                self.fields["mds"].disabled = True

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("date_reception") and cleaned["date_reception"] > timezone.localdate():
            self.add_error("date_reception", "La date de réception ne peut pas être dans le futur.")
        if cleaned.get("circuit") == DemandeRelationUsager.Circuit.MDS and not self.gestionnaire_sas:
            # Pour une demande reçue directement en MDS, le délai court dès la réception.
            cleaned["date_notification_mds"] = cleaned.get("date_reception")
            self.instance.date_notification_mds = cleaned.get("date_reception")
        if cleaned.get("circuit") == DemandeRelationUsager.Circuit.MDS and not cleaned.get("mds"):
            self.add_error("mds", "Choisissez la MDS chargée de l'évaluation.")
        if cleaned.get("accompagnement_autre_service") and not cleaned.get("usager_informe_liaison"):
            self.add_error("usager_informe_liaison", "Confirmez si l'usager a été informé de la liaison avec l'autre service.")
        if not self.gestionnaire_sas:
            mds = cleaned.get("mds") or self.instance.mds
            if not mds or not self.user.a_acces_mds(mds):
                self.add_error("mds", "Vous ne pouvez pas créer une demande hors de votre MDS.")
            cleaned["circuit"] = DemandeRelationUsager.Circuit.MDS
        return cleaned


class TransmissionMDSForm(forms.Form):
    mds = forms.ModelChoiceField(queryset=MDS.objects.none(), label="MDS choisie")
    agent = forms.ModelChoiceField(queryset=User.objects.none(), label="Travailleur social destinataire")

    def __init__(self, *args, demande, **kwargs):
        super().__init__(*args, **kwargs)
        self.demande = demande
        self.fields["mds"].queryset = MDS.objects.filter(active=True).order_by("nom")
        self.fields["agent"].queryset = User.objects.filter(
            is_active=True, profils_mds__mds_id=demande.mds_id, profils_mds__actif=True,
            profils_mds__herite_de__isnull=True,
        ).distinct().order_by("last_name", "first_name")
        if demande.mds_id:
            self.initial["mds"] = demande.mds_id
            self.fields["mds"].disabled = True
        _style_fields(self)

    def clean(self):
        cleaned = super().clean()
        mds, agent = cleaned.get("mds"), cleaned.get("agent")
        if mds and agent and not UserMDSProfile.objects.filter(
            user=agent, mds=mds, actif=True, herite_de__isnull=True
        ).exists():
            self.add_error("agent", "Le travailleur social doit être rattaché à la MDS choisie.")
        return cleaned


class TraitementRUForm(forms.ModelForm):
    class Meta:
        model = DemandeRelationUsager
        fields = [
            "agent_assigne", "elements_declaratifs", "evaluation_sociale", "modalites_contact",
            "situation_actualisee", "date_premier_rendez_vous", "heure_premier_rendez_vous",
            "absence_premier_rendez_vous", "date_second_rendez_vous", "heure_second_rendez_vous",
            "absence_second_rendez_vous", "problematique_plan",
            "plan_aide", "propositions_reorientation", "aide_financiere_type", "aide_financiere_proposee",
            "decision_aide_financiere", "date_aide_financiere", "montant_aide_financiere", "motif_rejet_aide",
        ]
        widgets = {
            "date_premier_rendez_vous": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "heure_premier_rendez_vous": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "date_second_rendez_vous": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "heure_second_rendez_vous": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "date_aide_financiere": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "elements_declaratifs": forms.Textarea(attrs={"rows": 3}),
            "evaluation_sociale": forms.Textarea(attrs={"rows": 4}),
            "modalites_contact": forms.Textarea(attrs={"rows": 3}),
            "situation_actualisee": forms.Textarea(attrs={"rows": 4}),
            "problematique_plan": forms.Textarea(attrs={"rows": 5}),
            "plan_aide": forms.Textarea(attrs={"rows": 4}),
            "propositions_reorientation": forms.Textarea(attrs={"rows": 3}),
            "motif_rejet_aide": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user, instance, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        worker_ids = UserMDSProfile.objects.filter(
            mds=instance.mds, actif=True, user__is_active=True, herite_de__isnull=True
        ).values_list("user_id", flat=True) if instance.mds_id else []
        self.fields["agent_assigne"].queryset = User.objects.filter(id__in=worker_ids).order_by("last_name", "first_name")
        self.user = user
        _style_fields(self)
        if not (user.is_superuser or user.a_la_capacite("peut_valider")):
            self.fields.pop("agent_assigne")

    def clean(self):
        cleaned = super().clean()
        montant = cleaned.get("montant_aide_financiere")
        if montant is not None and montant < 0:
            self.add_error("montant_aide_financiere", "Le montant ne peut pas être négatif.")
        if cleaned.get("aide_financiere_proposee") and not cleaned.get("decision_aide_financiere"):
            self.add_error("decision_aide_financiere", "Indiquez la décision relative à l'aide financière.")
        if cleaned.get("absence_premier_rendez_vous") and not cleaned.get("date_second_rendez_vous"):
            self.add_error("date_second_rendez_vous", "Indiquez la date du second rendez-vous proposé.")
        return cleaned


class FicheRetourSASForm(forms.ModelForm):
    usager_informe_transmission = forms.BooleanField(
        label="Usager informé de la réponse et des éléments transmis", required=False,
    )
    date_information_usager = forms.DateField(
        label="Date d'information de l'usager", required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    class Meta:
        model = FicheRetourSAS
        fields = ["type_reponse", "synthese_reponse", "service_reoriente", "suite_donnee"]
        widgets = {
            "synthese_reponse": forms.Textarea(attrs={"rows": 5}),
            "suite_donnee": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "synthese_reponse": "Texte de réponse destiné à l'usager et au service émetteur; ne reprendre que les informations communicables.",
        }

    def __init__(self, *args, demande=None, **kwargs):
        super().__init__(*args, **kwargs)
        demande = demande or getattr(self.instance, "demande", None)
        if demande:
            self.initial.setdefault("usager_informe_transmission", demande.usager_informe_transmission)
            self.initial.setdefault("date_information_usager", demande.date_information_usager)
        _style_fields(self)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("usager_informe_transmission") and not cleaned.get("date_information_usager"):
            self.add_error("date_information_usager", "Indiquez la date d'information de l'usager.")
        return cleaned


class PieceRUForm(forms.Form):
    titre = forms.CharField(max_length=255, label="Titre de la pièce", widget=forms.TextInput(attrs={"class": STYLE}))
    fichier = forms.FileField(label="Document PDF", widget=forms.ClearableFileInput(attrs={"class": STYLE}))

    def __init__(self, *args, type_document=None, **kwargs):
        self.type_document = type_document
        super().__init__(*args, **kwargs)

    def clean_fichier(self):
        fichier = self.cleaned_data["fichier"]
        if self.type_document:
            from ged.validation import erreurs_fichier
            erreurs = erreurs_fichier(fichier, self.type_document)
            if erreurs:
                raise ValidationError(erreurs)
        return fichier
