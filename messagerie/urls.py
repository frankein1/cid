# messagerie/urls.py - AJOUTER LA ROUTE DE RECHERCHE
from django.urls import path
from . import views

app_name = 'messagerie'

urlpatterns = [
    path('', views.boite_reception, name='boite_reception'),
    path('envoyes/', views.messages_envoyes, name='messages_envoyes'),
    path('nouveau/', views.nouveau_message, name='nouveau_message'),
    path('nouveau/<int:beneficiaire_id>/', views.nouveau_message, name='nouveau_message_beneficiaire'),
    path('message/<int:message_id>/', views.voir_message, name='voir_message'),
    path('repondre/<int:message_id>/', views.repondre_message, name='repondre_message'),
    path('api/nb-non-lus/', views.nb_messages_non_lus, name='nb_non_lus'),
    path('api/rechercher-beneficiaire/', views.rechercher_beneficiaire, name='rechercher_beneficiaire'),  # NOUVEAU
]
