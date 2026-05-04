# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# protection_enfance/admin.py - CORRIGÉ ET PROPRE
from django.contrib import admin
from .models.informations_preoccupantes import InformationPreoccupante, HistoriqueAction, NumeroCounter

# ✅ MODÈLES EXISTANTS
@admin.register(InformationPreoccupante)
class InformationPreoccupanteAdmin(admin.ModelAdmin):
    list_display = ['numero', 'enfant_nom', 'statut', 'date_creation']
    list_filter = ['statut', 'origine']
    search_fields = ['numero', 'enfant_nom']
    date_hierarchy = 'date_creation'

@admin.register(HistoriqueAction)
class HistoriqueActionAdmin(admin.ModelAdmin):
    list_display = ['information', 'action', 'user', 'date']
    list_filter = ['action', 'date']
    search_fields = ['information__numero', 'action']
    date_hierarchy = 'date'

@admin.register(NumeroCounter)
class NumeroCounterAdmin(admin.ModelAdmin):
    list_display = ['prefix', 'last_value']
    list_filter = ['prefix']

# ❌ MODÈLES À DÉCOMMENTER QUAND ILS EXISTERONT

# @admin.register(SignalementCRIP)
# class SignalementCRIPAdmin(admin.ModelAdmin):
#     list_display = ['numero_signalement', 'origine', 'date_reception']
#     list_filter = ['origine']
#     search_fields = ['numero_signalement']
#     date_hierarchy = 'date_reception'

# @admin.register(EnqueteSociale)
# class EnqueteSocialeAdmin(admin.ModelAdmin):
#     list_display = ['information_preoccupante', 'evaluateur', 'date_validation']
#     list_filter = ['date_validation']
#     search_fields = ['information_preoccupante__numero']

# @admin.register(Placement)
# class PlacementAdmin(admin.ModelAdmin):
#     list_display = ['enfant', 'type_placement', 'date_debut', 'statut']
#     list_filter = ['type_placement', 'statut']
#     search_fields = ['enfant__nom']
#     date_hierarchy = 'date_debut'

# @admin.register(FamilleAccueil)
# class FamilleAccueilAdmin(admin.ModelAdmin):
#     list_display = ['agrement', 'nombre_places', 'statut_agrement']
#     list_filter = ['statut_agrement']
#     search_fields = ['agrement']

# @admin.register(ProcedureAdoption)
# class ProcedureAdoptionAdmin(admin.ModelAdmin):
#     list_display = ['enfant', 'type_adoption', 'date_depot_demande', 'date_jugement']
#     list_filter = ['type_adoption']
#     search_fields = ['enfant__nom']

# @admin.register(MesureEducative)
# class MesureEducativeAdmin(admin.ModelAdmin):
#     list_display = ['enfant', 'type_mesure', 'date_debut', 'date_fin_prevue']
#     list_filter = ['type_mesure']
#     search_fields = ['enfant__nom']
