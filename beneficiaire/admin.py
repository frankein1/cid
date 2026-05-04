# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

"""
Administration Django pour l'application bénéficiaire - VERSION RÉSEAU FAMILIAL
Fichier : beneficiaire/admin.py
✅ CRÉATION OK + LIENS AFFICHAGE SANS ERREUR
"""

from django.contrib import admin
from .models import Beneficiaire, DocumentBeneficiaireLink, LienFamilial

# ---------------------------------------------------------------------
# INLINE LIENS FAMILIAUX - LECTURE SEULE (SANS ERREUR)
# ---------------------------------------------------------------------
class LienFamilialInline(admin.TabularInline):
    model = LienFamilial
    fk_name = "personne_a"
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ['personne_b', 'type_lien', 'vit_au_foyer']
    readonly_fields = ['personne_b', 'type_lien', 'vit_au_foyer']
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Beneficiaire)
class BeneficiaireAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'code_interne', 'mds', 'statut', 'compte_liens')  # ✅ Nom différent
    list_filter = ('statut', 'mds', 'civilite')
    search_fields = ('nom', 'prenom', 'code_interne', 'nir')
    
    readonly_fields = ['code_interne', 'date_creation', 'date_modification']
    
    inlines = [LienFamilialInline]
    
    fieldsets = (
        ('Identification', {'fields': ('code_interne', 'statut')}),
        ('Informations Personnelles', {
            'fields': ('civilite', 'nom', 'prenom', 'nom_naissance', 'date_naissance', 'lieu_naissance', 'marital_status')
        }),
        ('Coordonnées', {
            'fields': ('telephone_mobile', 'telephone_fixe', 'email', 'adresse', 'code_postal', 'ville')
        }),
        ('Informations Administratives', {
            'fields': ('nir', 'numero_caf', 'numero_france_travail', 'numero_fiscal', 'date_entree', 'date_sortie', 'motif_sortie', 'detail_sortie')
        }),
        ('Rattachement', {'fields': ('mds', 'referent_mds')}),
        ('Tracking', {
            'fields': ('date_creation', 'date_modification', 'cree_par'),
            'classes': ('collapse',), 
        }),
    )
    
    def compte_liens(self, obj):
        """✅ SANS format_html - simple texte"""
        if not obj:
            return "0"
        try:
            count = obj.liens_familiaux.count()
            return f"{count}" if count > 0 else "0"
        except:
            return "0"
    compte_liens.short_description = "Liens"

@admin.register(LienFamilial)
class LienFamilialAdmin(admin.ModelAdmin):
    list_display = ('personne_a', 'type_lien', 'personne_b', 'vit_au_foyer')
    list_filter = ('type_lien', 'vit_au_foyer')
    search_fields = ('personne_a__nom', 'personne_b__nom')

@admin.register(DocumentBeneficiaireLink)
class DocumentBeneficiaireLinkAdmin(admin.ModelAdmin):
    list_display = ['beneficiaire', 'type_document', 'document_ged', 'valide', 'date_creation']
    list_filter = ['type_document', 'valide', 'date_creation']
    search_fields = ['beneficiaire__nom', 'beneficiaire__prenom', 'document_ged__titre']
    readonly_fields = ['date_creation']
    
    fieldsets = (
        ('Liaison', {'fields': ('beneficiaire', 'document_ged', 'type_document')}),
        ('Validation', {'fields': ('valide',)}),
        ('Métadonnées', {
            'fields': ('date_creation', 'cree_par'),
            'classes': ('collapse',),
        }),
    )
