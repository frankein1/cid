# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/admin.py
from django.contrib import admin

from .models import (ActionIP, EnfantIP, HistoriqueAction, InformationPreoccupante, NumeroCounter,
                     RapportIP, SaisineIP)


class EnfantInline(admin.TabularInline):
    model = EnfantIP
    extra = 0
    raw_id_fields = ('beneficiaire',)


@admin.register(InformationPreoccupante)
class InformationPreoccupanteAdmin(admin.ModelAdmin):
    list_display = ['numero', 'date_reception_crip', 'mds', 'statut', 'date_echeance']
    list_filter = ['statut', 'origine', 'mds']
    search_fields = ['numero', 'famille_libelle', 'famille__nom']
    date_hierarchy = 'date_reception_crip'
    raw_id_fields = ('famille',)
    inlines = [EnfantInline]


@admin.register(HistoriqueAction)
class HistoriqueActionAdmin(admin.ModelAdmin):
    list_display = ['information', 'action', 'user', 'date']
    search_fields = ['information__numero', 'action']
    date_hierarchy = 'date'


@admin.register(ActionIP)
class ActionIPAdmin(admin.ModelAdmin):
    list_display = ['ip', 'type_action', 'date', 'resultat', 'auteur']
    list_filter = ['type_action', 'resultat']


admin.site.register(SaisineIP)
admin.site.register(RapportIP)
admin.site.register(NumeroCounter)
