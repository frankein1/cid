# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/urls.py
from django.urls import path

from . import views

app_name = "ru"
urlpatterns = [
    path("", views.liste, name="liste"),
    path("creer/", views.creer, name="creer"),
    path("<int:pk>/formulaire.pdf", views.formulaire_pdf, name="formulaire_pdf"),
    path("<int:pk>/fiche-retour.pdf", views.fiche_retour_pdf, name="fiche_retour_pdf"),
    path("<int:pk>/courrier-rdv/<int:rang>.pdf", views.courrier_rdv_pdf, name="courrier_rdv_pdf"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/modifier/", views.modifier, name="modifier"),
    path("<int:pk>/transmettre-mds/", views.transmettre_mds, name="transmettre_mds"),
    path("<int:pk>/traitement/", views.traitement, name="traitement"),
    path("<int:pk>/fiche-retour/", views.fiche_retour, name="fiche_retour"),
    path("<int:pk>/action/", views.action, name="action"),
    path("<int:pk>/pieces/ajouter/", views.ajouter_piece, name="ajouter_piece"),
]
