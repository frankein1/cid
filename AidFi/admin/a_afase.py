# AidFi/admin/a_afase.py

from django.contrib import admin
from AidFi.models.m_afase import DemandeAFASE


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

    readonly_fields = ()
