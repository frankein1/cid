# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# adultevul/urls.py
from django.urls import path

from . import views

app_name = "adultevul"
urlpatterns = [
    path("", views.liste, name="liste"),
    path("recueillir/", views.creer, name="creer"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/qualifier/", views.qualifier_view, name="qualifier"),
    path("<int:pk>/cellule/", views.cellule, name="cellule"),
    path("<int:pk>/soumettre/", views.soumettre, name="soumettre"),
    path("<int:pk>/viser/", views.viser, name="viser"),
    path("<int:pk>/renvoyer/", views.renvoyer, name="renvoyer"),
    path("<int:pk>/decider/", views.decider_view, name="decider"),
    path("<int:pk>/cloturer/", views.cloturer_view, name="cloturer"),
    path("<int:pk>/protection/", views.protection, name="protection"),
    path("<int:pk>/masp/", views.masp, name="masp"),
    path("<int:pk>/annexe/<str:numero>.pdf", views.annexe_pdf, name="annexe_pdf"),
]
