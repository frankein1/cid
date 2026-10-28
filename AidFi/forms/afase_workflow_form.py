# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/forms/afase_workflow_form.py
"""
Saisie d'une demande d'AFASE, sur le modèle du formulaire de la note de service (annexe 1)
et des éléments de contenu de l'évaluation sociale (annexe 2).
"""

from decimal import Decimal
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction

from AidFi.models.m_afase import (
    DemandeAFASE,
    EvaluationSocialeAFASE,
    BudgetAFASE,
    EnfantAFASE,
    CODES_INSTRUCTION_AFASE,
    nb_personnes_au_foyer,
)
from AidFi.services import budget_afase
from AidFi.models.m_generique import TypeAide, PieceJustificative
from beneficiaire.models import Beneficiaire, LienFamilial
from ged.models import DocumentGED


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
    plan_action = forms.CharField(widget=forms.Textarea, required=False,
                                  label="Plan d'action élaboré avec la famille")
    adhesion_famille = forms.ChoiceField(choices=[("", "---------")] + EvaluationSocialeAFASE.ADHESIONS,
                                         required=False, label="Degré d'adhésion de la famille au plan d'aide")
    affectation_aide = forms.CharField(max_length=255, required=False, label="Affectation ciblée de l'aide")
    parcours_insertion = forms.CharField(widget=forms.Textarea, required=False,
                                         label="Parcours d'insertion (jeunes de 16 à 21 ans sans scolarité ni stage)")

    # Demandeur (cadre B du formulaire)
    lien_demandeur = forms.ChoiceField(choices=[("", "---------")] + DemandeAFASE.LIENS_DEMANDEUR, required=False,
                                       label="Lien avec l'enfant")
    date_signature_demandeur = forms.DateField(required=False, label="Date de signature du demandeur",
                                               widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    allocataire_caf = forms.NullBooleanField(required=False, label="Allocataire CAF", widget=forms.NullBooleanSelect)
    situation_pro_demandeur = forms.CharField(max_length=200, required=False, label="Situation professionnelle")
    situation_pro_conjoint = forms.CharField(max_length=200, required=False,
                                             label="Âge et situation professionnelle du conjoint")
    historique_aides = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False,
                                       label="Historique des aides ASE des 12 derniers mois")
    autres_aides_sollicitees = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False,
                                               label="Autres aides sollicitées (dates, organismes, décisions, montants)")
    qualite_ts = forms.ChoiceField(choices=[("", "---------")] + DemandeAFASE.QUALITES_TS, required=False,
                                   label="Qualité du travailleur social")
    nb_personnes_foyer = forms.IntegerField(min_value=1, max_value=30, label="Nombre de personnes vivant au foyer")

    documents_ged = forms.ModelMultipleChoiceField(queryset=DocumentGED.objects.none(), required=False, widget=forms.CheckboxSelectMultiple, label="Documents GED à joindre à la demande")
    

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
        for f in self.fields.values():
            if isinstance(f.widget, forms.Textarea):
                f.widget.attrs.setdefault("class", "form-textarea w-full")
                f.widget.attrs.setdefault("rows", 4)
            elif not isinstance(f.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.HiddenInput)):
                f.widget.attrs.setdefault("class", "form-input w-full")
        if beneficiaire: self.fields['documents_ged'].queryset = DocumentGED.objects.filter(content_type=ContentType.objects.get_for_model(beneficiaire), object_id=beneficiaire.id)

        if demande:
            self.initial.update({
                "demandeur": getattr(demande, "demandeur", None),
                "numero_genesis": demande.numero_genesis,
                "premiere_demande": demande.premiere_demande,
                "avis_ts": demande.avis_ts,
                "montant_sollicite": demande.montant_sollicite,
                "duree_demande": demande.duree_demande,
                "lien_demandeur": demande.lien_demandeur,
                "date_signature_demandeur": demande.date_signature_demandeur,
                "allocataire_caf": demande.allocataire_caf,
                "situation_pro_demandeur": demande.situation_pro_demandeur,
                "situation_pro_conjoint": demande.situation_pro_conjoint,
                "historique_aides": demande.historique_aides,
                "autres_aides_sollicitees": demande.autres_aides_sollicitees,
                "qualite_ts": demande.qualite_ts,
            })
            if hasattr(demande, "evaluation_afase"):
                eval_obj = demande.evaluation_afase
                self.initial.update({
                    "code_instruction": eval_obj.code_instruction,
                    "situation_sociale": eval_obj.situation_sociale,
                    "analyse_problematique": eval_obj.analyse_problematique,
                    "justification_demande": eval_obj.justification_demande,
                    "commentaire_familial": eval_obj.commentaire_familial,
                    "plan_action": eval_obj.plan_action,
                    "adhesion_famille": eval_obj.adhesion_famille,
                    "affectation_aide": eval_obj.affectation_aide,
                    "parcours_insertion": eval_obj.parcours_insertion,
                })
            if hasattr(demande, "budget"):
                budget = demande.budget
                self.initial.update({
                    "total_ressources": budget.totaux["ressources"],
                    "total_charges": budget.totaux["charges_payees"],
                    "reste_a_vivre": budget.reste_a_vivre,
                    "nb_personnes_foyer": budget.nb_personnes_foyer,
                })
        else:
            if beneficiaire.numero_genesis:
                self.initial["numero_genesis"] = beneficiaire.numero_genesis
            self.initial["historique_aides"] = historique_aides_cid(beneficiaire)
            self.initial["allocataire_caf"] = True if beneficiaire.numero_caf else None
        self.initial.setdefault("nb_personnes_foyer", nb_personnes_au_foyer(beneficiaire))

    def clean(self):
        cleaned = super().clean()
        # Budget structuré (rubriques du formulaire officiel), lu directement dans les champs envoyés
        ressources, charges, dettes = budget_afase.depuis_post(self.data)
        cleaned["ressources"], cleaned["charges"], cleaned["dettes"] = ressources, charges, dettes
        t = budget_afase.totaux(ressources, charges, cleaned.get("nb_personnes_foyer") or 1)
        cleaned["total_ressources"] = t["ressources"]
        cleaned["total_charges"] = t["charges_payees"]
        cleaned["reste_a_vivre"] = t["reste_a_vivre"]
        cleaned["enfants"] = self._enfants_post()
        if not any(e["concerne"] for e in cleaned["enfants"]):
            self.add_error(None, "Cochez au moins un enfant concerné par la demande (ou un enfant à naître).")
        return cleaned

    def _enfants_post(self):
        """Lignes e__<i>__… du cadre A : enfants de la famille et éventuel enfant à naître."""
        from datetime import date
        enfants = []
        for i in range(30):
            pre = f"e__{i}__"
            if not any(k.startswith(pre) for k in self.data.keys()):
                continue
            a_naitre = bool(self.data.get(pre + "a_naitre"))
            nom = (self.data.get(pre + "nom") or "").strip()
            if not nom and not a_naitre:
                continue
            try:
                naissance = date.fromisoformat(self.data.get(pre + "date_naissance") or "")
            except ValueError:
                naissance = None
            benef = self.data.get(pre + "beneficiaire") or ""
            enfants.append({
                "beneficiaire_id": int(benef) if benef.isdigit() else None,
                "nom": nom[:60], "prenom": (self.data.get(pre + "prenom") or "").strip()[:60],
                "date_naissance": naissance, "sexe": (self.data.get(pre + "sexe") or "")[:1],
                "situation": (self.data.get(pre + "situation") or "").strip()[:150],
                "a_naitre": a_naitre, "concerne": bool(self.data.get(pre + "concerne")),
            })
        return enfants

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
        for champ in ("lien_demandeur", "situation_pro_demandeur", "situation_pro_conjoint", "historique_aides",
                      "autres_aides_sollicitees", "qualite_ts"):
            setattr(demande, champ, self.cleaned_data.get(champ) or "")
        demande.date_signature_demandeur = self.cleaned_data.get("date_signature_demandeur")
        demande.allocataire_caf = self.cleaned_data.get("allocataire_caf")
        demande.save()
        demande.enfants.all().delete()
        for e in self.cleaned_data["enfants"]:
            EnfantAFASE.objects.create(demande=demande, **e)

        EvaluationSocialeAFASE.objects.update_or_create(
            demande=demande, defaults={
                "code_instruction": self.cleaned_data["code_instruction"],
                "situation_sociale": self.cleaned_data["situation_sociale"],
                "analyse_problematique": self.cleaned_data["analyse_problematique"],
                "justification_demande": self.cleaned_data["justification_demande"],
                "commentaire_familial": self.cleaned_data["commentaire_familial"],
                "plan_action": self.cleaned_data["plan_action"],
                "adhesion_famille": self.cleaned_data["adhesion_famille"],
                "affectation_aide": self.cleaned_data["affectation_aide"],
                "parcours_insertion": self.cleaned_data["parcours_insertion"],
            },
        )

        BudgetAFASE.objects.update_or_create(
            demande=demande, defaults={"ressources": self.cleaned_data["ressources"],
                                       "charges": self.cleaned_data["charges"],
                                       "dettes": self.cleaned_data["dettes"],
                                       "nb_personnes_foyer": self.cleaned_data["nb_personnes_foyer"]})

        # Liaison des documents GED à la demande AFASE (via PieceJustificative)
        for doc in self.cleaned_data.get('documents_ged', []):
            PieceJustificative.objects.get_or_create(demande=demande, document_ged=doc, defaults={'type_piece': 'AUTRE', 'statut': 'VALIDE'})

        return demande


def enfants_proposes(beneficiaire, demande=None):
    """
    Lignes du cadre A : enfants déjà saisis sur la demande, sinon enfants de la famille de moins de 21 ans
    repris du réseau familial (cochés par défaut s'ils vivent au foyer).
    """
    from dateutil.relativedelta import relativedelta
    from django.utils import timezone
    if demande is not None and demande.enfants.exists():
        return [{"beneficiaire_id": e.beneficiaire_id, "nom": e.nom, "prenom": e.prenom,
                 "date_naissance": e.date_naissance, "sexe": e.sexe, "situation": e.situation,
                 "a_naitre": e.a_naitre, "concerne": e.concerne} for e in demande.enfants.all()]
    lignes = []
    for m in beneficiaire.reseau_familial():
        p = m["personne"]
        if m["type_lien"] == "ENFANT" and p.date_naissance and \
                relativedelta(timezone.localdate(), p.date_naissance).years < 21:
            lignes.append({"beneficiaire_id": p.pk, "nom": p.nom, "prenom": p.prenom,
                           "date_naissance": p.date_naissance,
                           "sexe": "M" if p.civilite == "M." else ("F" if p.civilite == "MME" else ""),
                           "situation": "", "a_naitre": False, "concerne": m["vit_au_foyer"]})
    return lignes


def historique_aides_cid(beneficiaire):
    """Aides de CID des 12 derniers mois pour la famille (proposé dans l'historique, modifiable)."""
    from datetime import timedelta
    from django.utils import timezone
    from AidFi.models.m_generique import DemandeAide
    ids = {beneficiaire.pk} | {m["personne"].pk for m in beneficiaire.reseau_familial()}
    depuis = timezone.now() - timedelta(days=365)
    lignes = []
    for d in DemandeAide.objects.filter(beneficiaire_id__in=ids, date_creation__gte=depuis)\
            .exclude(statut="BROUILLON").select_related("type_aide").order_by("date_creation"):
        lignes.append(f"- {timezone.localtime(d.date_creation):%d/%m/%Y} : {d.type_aide.nom if d.type_aide else 'Aide'} – "
                      f"{d.get_statut_display()}" + (f" – {d.montant_sollicite} € demandés" if d.montant_sollicite else ""))
    return "\n".join(lignes)
