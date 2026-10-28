# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/admin/a_referentiel.py
"""Référentiel d'aide à la décision AFASE et paramètres : saisis d'après la note de service en vigueur."""
from django.contrib import admin

from AidFi.models.m_referentiel import MontantIndicatifAFASE, ParametresAides, ReferentielMotifAFASE


@admin.register(ParametresAides)
class ParametresAidesAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'seuil_montant_controle', 'seuil_nb_aides_12_mois', 'regie_montant_max']

    def has_add_permission(self, request):
        return not ParametresAides.objects.exists()   # une seule ligne


class MontantInline(admin.TabularInline):
    model = MontantIndicatifAFASE
    extra = 1


@admin.register(ReferentielMotifAFASE)
class ReferentielMotifAdmin(admin.ModelAdmin):
    list_display = ['code', 'libelle', 'actif']
    list_editable = ['actif']
    inlines = [MontantInline]
