# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# cid/urls.py 
"""
URL configuration for cid project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from core.views.vins import run_install

urlpatterns = [
    # ----------------------------------------------------
    # AUTHENTIFICATION
    # Utilise 'login.html' à la racine de /templates/
    # ----------------------------------------------------
    path("init-render/", run_install),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='logout.html'), name='logout'),
    
   
    #path(
#        'accounts/login/', 
#        auth_views.LoginView.as_view(template_name='login.html'), # <-- CORRECTION ICI
#        name='login'
#    ),
    
    # Déconnexion (la redirection sera gérée par settings.LOGOUT_REDIRECT_URL)
#    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
     
    # ----------------------------------------------------
    # URLS PRINCIPALES
    # ----------------------------------------------------
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='accueil.html'), name='accueil'),
    path('beneficiaire/', include('beneficiaire.urls')),
    path('', include('core.urls')),
    path('ged/', include('ged.urls')),
    path('mds/', include('mds.urls')),
    path('planning/', include('planning.urls')),
    path('AidFi/', include('AidFi.urls')),
    path('messagerie/', include('messagerie.urls')),
    #    path('protection-enfance/', include('protection_enfance.urls')),
]

# Servir les fichiers media en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
