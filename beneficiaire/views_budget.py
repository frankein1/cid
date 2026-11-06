# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/views_budget.py
"""Budget du foyer : consultation (historique compris), nouveau budget pré-rempli, modification."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from AidFi.models.m_afase import nb_personnes_au_foyer
from AidFi.services import budget_afase as ref

from .budget import budget_en_cours, dernier_budget_afase, foyer_meme_mds
from .models import Beneficiaire
from .models_budget import BudgetFoyer
from .views import user_peut_agir_sur_beneficiaire


class EnteteBudgetForm(forms.Form):
    date_etabli = forms.DateField(label="Établi le", widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    nb_personnes_foyer = forms.IntegerField(min_value=1, max_value=30, label="Personnes vivant au foyer",
                                            widget=forms.NumberInput(attrs={'class': 'w-20 px-2 py-1 border rounded text-center'}))
    commentaire = forms.CharField(label="Observations", required=False, widget=forms.Textarea(attrs={'rows': 3}),
                                  help_text=BudgetFoyer._meta.get_field('commentaire').help_text)


def _usager(request, code_interne, ecriture=False):
    b = get_object_or_404(Beneficiaire.tous.select_related('mds'), code_interne=code_interne)
    if b.niveau_acces(request.user) != 'complet':
        return b, HttpResponseForbidden("Le budget du foyer fait partie du dossier complet de la MDS de l'usager.")
    if ecriture and not user_peut_agir_sur_beneficiaire(request.user, b):
        return b, HttpResponseForbidden("Modification réservée aux agents de la MDS de l'usager.")
    return b, None


@login_required
def budget_foyer(request, code_interne):
    b, refus = _usager(request, code_interne)
    if refus:
        return refus
    foyer = foyer_meme_mds(b)
    historique = BudgetFoyer.objects.filter(beneficiaire_id__in=foyer | {b.pk}).select_related('beneficiaire', 'cree_par')
    return render(request, 'beneficiaire/budget_foyer.html', {
        'beneficiaire': b, 'budget': budget_en_cours(b), 'historique': historique,
        'peut_modifier': user_peut_agir_sur_beneficiaire(request.user, b),
        'budget_afase': dernier_budget_afase(b),
    })


@login_required
def budget_foyer_form(request, code_interne, pk=None):
    b, refus = _usager(request, code_interne, ecriture=True)
    if refus:
        return refus
    budget = get_object_or_404(BudgetFoyer, pk=pk, beneficiaire=b) if pk else None
    source, origine = budget, None
    if budget is None:
        if request.GET.get('depuis') == 'afase':
            source = dernier_budget_afase(b)
            origine = f"repris du budget de la demande d'AFASE du {source.demande.date_creation:%d/%m/%Y}" if source else None
        else:
            source = budget_en_cours(b)
            if source:
                origine = f"repris du budget du {source.date_etabli:%d/%m/%Y}" + (
                    f" (établi sur la fiche de {source.beneficiaire.prenom} {source.beneficiaire.nom})"
                    if source.beneficiaire_id != b.pk else "") + " : mettez à jour ce qui a changé"
    if request.method == 'POST':
        entete = EnteteBudgetForm(request.POST)
        ressources, charges, dettes = ref.depuis_post(request.POST)
        if entete.is_valid():
            cible = budget or BudgetFoyer(beneficiaire=b, cree_par=request.user)
            cible.date_etabli = entete.cleaned_data['date_etabli']
            cible.nb_personnes_foyer = entete.cleaned_data['nb_personnes_foyer']
            cible.commentaire = entete.cleaned_data['commentaire']
            cible.ressources, cible.charges, cible.dettes = ressources, charges, dettes
            cible.modifie_par = request.user
            cible.save()
            messages.success(request, "Budget du foyer enregistré.")
            return redirect('beneficiaire:budget_foyer', code_interne=b.code_interne)
    else:
        entete = EnteteBudgetForm(initial={
            'date_etabli': budget.date_etabli if budget else timezone.localdate(),
            'nb_personnes_foyer': source.nb_personnes_foyer if source else nb_personnes_au_foyer(b),
            'commentaire': budget.commentaire if budget else ''})
        ressources = source.ressources if source else {}
        charges = source.charges if source else {}
        dettes = list(source.dettes or []) if source else []
    dettes = dettes + [{"creancier": "", "montant": ""} for _ in range(max(3 - len(dettes), 1))]
    return render(request, 'beneficiaire/budget_foyer_form.html', {
        'beneficiaire': b, 'budget': budget, 'form': entete, 'origine': origine,
        'grille': ref.grille(ressources, charges), 'dettes': dettes,
        'rubriques_ressources': ref.RESSOURCES, 'rubriques_charges': ref.CHARGES,
        'colonnes_ressources': ref.COLONNES_RESSOURCES, 'colonnes_charges': ref.COLONNES_CHARGES,
        'a_preciser': ref.A_PRECISER, 'ancien_budget': None,
        'budget_afase': None if budget else dernier_budget_afase(b),
    })
