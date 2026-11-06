# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# beneficiaire/budget.py
"""Budget du foyer : retrouver le budget en cours d'un foyer, et faire le lien avec le budget des demandes d'AFASE."""
from .models import LienFamilial
from .models_budget import BudgetFoyer


def membres_du_foyer(beneficiaire):
    """Personnes liées qui vivent au foyer de l'usager (liens enregistrés dans un sens ou dans l'autre)."""
    ids = set()
    for lien in (LienFamilial.objects.filter(personne_a=beneficiaire, vit_au_foyer=True)
                 | LienFamilial.objects.filter(personne_b=beneficiaire, vit_au_foyer=True)):
        ids.add(lien.personne_b_id if lien.personne_a_id == beneficiaire.pk else lien.personne_a_id)
    ids.discard(beneficiaire.pk)
    return ids


def budget_en_cours(beneficiaire):
    """Le budget le plus récent de l'usager ; à défaut, celui d'une personne de son foyer (le budget est commun)."""
    propre = BudgetFoyer.objects.filter(beneficiaire=beneficiaire).first()
    if propre:
        return propre
    return BudgetFoyer.objects.filter(beneficiaire_id__in=membres_du_foyer(beneficiaire)).first()


def dernier_budget_afase(beneficiaire):
    from AidFi.models import BudgetAFASE
    return (BudgetAFASE.objects.filter(demande__beneficiaire=beneficiaire).select_related('demande')
            .order_by('-demande__date_creation', '-pk').first())
