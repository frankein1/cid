# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/admin.py
from django.contrib import admin

from .models import SituationExterne, JournalAppelAPI


@admin.register(SituationExterne)
class SituationExterneAdmin(admin.ModelAdmin):
    list_display = ('beneficiaire', 'source', 'statut_appel', 'resume', 'date_maj', 'maj_par', 'environnement')
    list_filter = ('source', 'statut_appel', 'environnement')
    search_fields = ('beneficiaire__nom', 'beneficiaire__code_interne')


@admin.register(JournalAppelAPI)
class JournalAppelAPIAdmin(admin.ModelAdmin):
    list_display = ('date', 'utilisateur', 'beneficiaire', 'source', 'code_http', 'statut_appel', 'environnement')
    list_filter = ('source', 'statut_appel', 'environnement')
    readonly_fields = [f.name for f in JournalAppelAPI._meta.fields]


from .models import CompteRDVSP, LienUsagerRDVSP, AppelRDVSP  # noqa: E402


@admin.register(CompteRDVSP)
class CompteRDVSPAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'agent_id', 'expire_le', 'date_maj')
    exclude = ('jeton_acces', 'jeton_renouvellement')   # les jetons ne s'affichent jamais
    readonly_fields = ('utilisateur', 'agent_id', 'expire_le', 'date_maj')


@admin.register(LienUsagerRDVSP)
class LienUsagerRDVSPAdmin(admin.ModelAdmin):
    list_display = ('beneficiaire', 'usager_rdvsp_id', 'date_creation')
    search_fields = ('beneficiaire__nom', 'beneficiaire__code_interne', 'usager_rdvsp_id')


@admin.register(AppelRDVSP)
class AppelRDVSPAdmin(admin.ModelAdmin):
    list_display = ('date', 'utilisateur', 'beneficiaire', 'action', 'code_http', 'reussi')
    list_filter = ('action', 'reussi')
    readonly_fields = [f.name for f in AppelRDVSP._meta.fields]
