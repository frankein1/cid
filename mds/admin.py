# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# mds/admin.py
from django.contrib import admin
from .models import MDS, MDSReception, DemiJourneeReception, UserMDSProfile

@admin.register(UserMDSProfile)
class UserMDSProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "mds", "principale", "actif", "date_debut"]
    list_filter = ["mds", "principale", "actif"]
    search_fields = ["user__last_name", "user__first_name", "user__username", "mds__nom"]
    autocomplete_fields = ["user", "mds"]
    list_editable = ["actif", "principale"]

@admin.register(MDS)
class MDSAdmin(admin.ModelAdmin):
    list_display = ["code_mds", "nom", "ville", "active", "get_utilisateurs_count"]
    list_filter = ["active", "ville"]
    search_fields = ["code_mds", "nom", "ville", "communes", "adresse"]

    fieldsets = (
        ("Identification", {
            "fields": ("code_mds", "nom", "active"),
        }),
        ("Localisation", {
            "fields": ("adresse", "code_postal", "ville", "departement", "communes"),
        }),
        ("Contact", {
            "fields": ("telephone", "email", "site_web"),
        }),
        ("Gestion", {
            "fields": ("responsable", "date_ouverture", "date_fermeture", "nb_agents_max"),
        }),
        ("Services et configuration", {
            "fields": ("services_proposes", "configuration"),
            "classes": ("collapse",),
        }),
    )

    def get_utilisateurs_count(self, obj):
        return obj.profils_utilisateurs.filter(actif=True).count()
    get_utilisateurs_count.short_description = "Agents Actifs"

@admin.register(MDSReception)
class MDSReceptionAdmin(admin.ModelAdmin):
    list_display = ["nom", "mds", "type_salle", "capacite", "actif"]
    list_filter = ["mds", "type_salle", "actif"]
    search_fields = ["nom", "mds__code_mds"]

@admin.register(DemiJourneeReception)
class DemiJourneeReceptionAdmin(admin.ModelAdmin):
    list_display = ("agent", "mds", "jour_semaine", "type_demi_journee", "actif")
    list_filter = ("mds", "agent", "jour_semaine", "actif")
    list_editable = ("actif",)
