# messagerie/admin.py
from django.contrib import admin
from .models import Message, StatutLecture

class MessageAdmin(admin.ModelAdmin):
    list_display = ['objet', 'expediteur', 'destinataire', 'copie', 'priorite', 'created_at']
    list_filter = ['priorite', 'categorie', 'created_at']
    search_fields = ['objet', 'contenu', 'expediteur__username', 'destinataire__username']
    raw_id_fields = ['expediteur', 'destinataire', 'copie', 'reponse_a']
    filter_horizontal = ['pieces_jointes']
    
    # OPTIONNEL - Organiser les champs dans l'interface
    fieldsets = (
        ('Participants', {
            'fields': ('expediteur', 'destinataire', 'copie')
        }),
        ('Contenu', {
            'fields': ('objet', 'contenu', 'priorite', 'categorie')
        }),
        ('Pièces jointes', {
            'fields': ('pieces_jointes',)
        }),
        ('Liaison', {
            'fields': ('reponse_a', 'content_type', 'object_id', 'reference'),
            'classes': ('collapse',)  # Section repliable
        }),
    )
    
    # OPTIONNEL - Champs en lecture seule
    readonly_fields = ['created_at', 'date_modification', 'cree_par', 'modifie_par']

@admin.register(StatutLecture)
class StatutLectureAdmin(admin.ModelAdmin):
    list_display = ['message', 'utilisateur', 'type_reception', 'lu', 'date_lecture']
    list_filter = ['lu', 'type_reception', 'date_lecture']
