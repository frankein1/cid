# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/admin/a_afase.py

from django.contrib import admin
from AidFi.models.m_afase import (
    DemandeAFASE,
    EvaluationSocialeAFASE,
    BudgetAFASE,
    DecisionAFASE,
)
from AidFi.models.afase_documents import DocumentAFASE


# ---------------------------------------------------------------------------
# INLINE DOCUMENTS GED
# ---------------------------------------------------------------------------

class DocumentAFASEInline(admin.TabularInline):
    model = DocumentAFASE
    extra = 0
    autocomplete_fields = ["document"]
    fields = ("document", "type_document", "obligatoire")
    verbose_name = "Document associé"
    verbose_name_plural = "Documents associés (GED)"


# ---------------------------------------------------------------------------
# INLINE ÉVALUATION / BUDGET / DÉCISION
# ---------------------------------------------------------------------------

class EvaluationSocialeInline(admin.StackedInline):
    model = EvaluationSocialeAFASE
    extra = 0


class BudgetAFASEInline(admin.StackedInline):
    model = BudgetAFASE
    extra = 0
    readonly_fields = ("nb_personnes_foyer", "reste_a_vivre")


class DecisionAFASEInline(admin.StackedInline):
    model = DecisionAFASE
    extra = 0


# ---------------------------------------------------------------------------
# DEMANDE AFASE
# ---------------------------------------------------------------------------

@admin.register(DemandeAFASE)
class DemandeAFASEAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "beneficiaire",
        "statut",
        "montant_sollicite",
        "duree_demande",
        "date_creation",
    )

    list_filter = ("statut",)

    search_fields = (
        "beneficiaire__nom",
        "beneficiaire__prenom",
        "numero_genesis",
    )

    ordering = ("-date_creation",)

    fieldsets = (
        ("Bénéficiaire", {
            "fields": ("beneficiaire", "numero_genesis", "premiere_demande")
        }),
        ("Proposition AFASE", {
            "fields": ("avis_ts", "montant_sollicite", "duree_demande")
        }),
        ("Statut", {
            "fields": ("statut",)
        }),
    )

    readonly_fields = ("date_creation",)

    inlines = [
        EvaluationSocialeInline,
        BudgetAFASEInline,
        DecisionAFASEInline,
        DocumentAFASEInline,
    ]
