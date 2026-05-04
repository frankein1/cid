# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# planning/admin.py
from django.contrib import admin
from .models import CreneauRdv, JourBloque

@admin.register(CreneauRdv)
class CreneauRdvAdmin(admin.ModelAdmin):
    list_display = ('date', 'heure_debut', 'heure_fin', 'salle', 'agent', 'type_rdv', 'statut')
    list_filter = ('date', 'type_rdv', 'statut', 'salle')
    search_fields = ('agent__last_name', 'agent__first_name', 'beneficiaire__nom', 'beneficiaire__prenom')
    date_hierarchy = 'date'
    ordering = ('-date', 'heure_debut')
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('date', 'heure_debut', 'heure_fin', 'salle', 'agent')
        }),
        ('Rendez-vous', {
            'fields': ('beneficiaire', 'type_rdv', 'statut', 'description')
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification', 'cree_par'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('date_creation', 'date_modification')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si c'est une création
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)

@admin.register(JourBloque)
class JourBloqueAdmin(admin.ModelAdmin):
    list_display = ('date', 'raison', 'salle', 'agent')
    list_filter = ('date', 'raison')
    search_fields = ('raison_detail',)
    date_hierarchy = 'date'
    actions = ['generer_feries']
   
    def save_model(self, request, obj, form, change):
        if not change:
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)
    
    @admin.action(description="Générer les jours fériés 2026")
    def generer_feries(self, request, queryset):
        # L'import est déplacé ici pour éviter les imports circulaires si nécessaire
        from planning.utils import generer_jours_feries_annee
        nb = generer_jours_feries_annee(2026)
        self.message_user(request, f"{nb} jours fériés 2026 ont été créés !")
