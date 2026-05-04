# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# ged/urls.py
from django.urls import path
from . import views

app_name = 'ged'

urlpatterns = [
    # ==========================================================================
    # DOCUMENTS LIÉS À UN BÉNÉFICIAIRE (Contexte spécifique)
    # ==========================================================================
    
    path('beneficiaires/<str:code_interne>/upload/', 
     views.DocumentUploadView.as_view(), 
     name='document_upload'), # J'ai harmonisé le nom ici (document_upload)

    path('beneficiaires/<str:code_interne>/documents/', 
     views.DocumentListView.as_view(), 
     name='beneficiary_documents'),
    
    # ==========================================================================
    # GESTION GÉNÉRALE DES DOCUMENTS
    # ==========================================================================
    
    path('documents/', 
         views.DocumentListView.as_view(), 
         name='document_list'),
         
    path('documents/<int:pk>/', 
         views.DocumentDetailView.as_view(), 
         name='document_detail'),
         
    path('documents/<int:pk>/edit/', 
         views.DocumentUpdateView.as_view(), 
         name='document_edit'),
    
    path('document-types/<int:pk>/edit/', 
         views.DocumentTypeUpdateView.as_view(), 
         name='document_type_edit'),
         
    path('documents/<int:pk>/delete/', 
         views.DocumentDeleteView.as_view(), 
         name='document_delete'),
         
    # Action spécifique de téléchargement (Stream de fichier)
    path('documents/<int:pk>/download/', 
         views.DownloadDocumentView.as_view(), 
         name='download_document'),
         
    path('documents/<int:pk>/validate/', 
         views.validate_document, 
         name='validate_document'),
             
    # ==========================================================================
    # CONFIGURATION / TYPES DE DOCUMENTS (Accès réservé MDS_Cadres / DITAS)
    # ==========================================================================
    
    path('document-types/', 
         views.DocumentTypeListView.as_view(), 
         name='document_type_list'),
         
    path('document-types/create/', 
         views.DocumentTypeCreateView.as_view(), 
         name='document_type_create'),
         
    path('document-types/<int:pk>/edit/', 
         views.DocumentTypeUpdateView.as_view(), 
         name='document_type_edit'),
]
