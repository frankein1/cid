# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# adultevul/admin.py
from django.contrib import admin

from .models import CelluleEvaluation, HistoriqueAV, SituationAdulteVulnerable


class CelluleInline(admin.StackedInline):
    model = CelluleEvaluation
    extra = 0


class HistoriqueInline(admin.TabularInline):
    model = HistoriqueAV
    extra = 0
    readonly_fields = ('date', 'auteur', 'action', 'detail')


@admin.register(SituationAdulteVulnerable)
class SituationAdmin(admin.ModelAdmin):
    list_display = ('numero', 'personne_nom', 'mds', 'statut', 'date_reception')
    list_filter = ('statut', 'mds')
    search_fields = ('numero', 'personne_nom', 'personne_prenom')
    readonly_fields = ('numero', 'date_creation', 'date_modification')
    inlines = [CelluleInline, HistoriqueInline]
