"""
ged/views.py - VERSION CONVERTIE CORE-DITAS 2026
Gestion Electronique des Documents avec stockage SeaweedFS
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    CreateView, DetailView, ListView, UpdateView, DeleteView
)
from django.urls import reverse_lazy
from django.http import FileResponse, HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views import View
from django.core.exceptions import PermissionDenied
from django.contrib.contenttypes.models import ContentType

from .models import (
    DocumentGED,
    DocumentType,
    HistoriqueDocument,
    DocumentCategorie,
)
from .forms import DocumentGEDForm
from .storage import SeaweedFSStorage

from mds.models import UserMDSProfile
from beneficiaire.models import Beneficiaire
try:
    from mds.models import UserMDSProfile
except ImportError:
    UserMDSProfile = None

logger = logging.getLogger(__name__)


# =============================================================================
# UPLOAD DOCUMENT
# =============================================================================

class DocumentUploadView(LoginRequiredMixin, CreateView):
    """
    Téléversement de documents liés à un bénéficiaire.
    Sécurité :
    - capacité 'peut_creer'
    - barrière territoriale MDS
    """
    model = DocumentGED
    form_class = DocumentGEDForm
    template_name = 'ged/document_upload.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.a_la_capacite('peut_creer'):
            raise PermissionDenied(
                "Vous n'avez pas la capacité d'ajouter des documents."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        code_interne = self.kwargs.get('code_interne')
        context['beneficiaire'] = get_object_or_404(
            Beneficiaire, code_interne=code_interne
        )
        return context

    def form_valid(self, form):
        code_interne = self.kwargs.get('code_interne')
        beneficiary = get_object_or_404(
            Beneficiaire, code_interne=code_interne
        )

        # --- BARRIÈRE TERRITORIALE ---
        if not beneficiary.peut_etre_vu_par(self.request.user):
            return HttpResponseForbidden(
                "Accès refusé : périmètre territorial non autorisé."
            )

        file = self.request.FILES.get('file')
        document = form.save(commit=False)

        # Liaison GenericFK
        document.content_object = beneficiary
        document.uploaded_by = self.request.user
        document._uploaded_file = file  # hash + taille

        # --- STOCKAGE SEAWEEDFS ---
        storage = SeaweedFSStorage()
        try:
            document.seaweedfs_id = storage.save(file.name, file)
        except Exception:
            form.add_error('file', "Erreur technique de stockage.")
            return self.form_invalid(form)

        document.save()
        form.save_m2m()

        # --- AUDIT ---
        document.log_action(
            'CREATION',
            self.request.user,
            f"Document lié au bénéficiaire {beneficiary.nom}",
            self.request,
        )

        messages.success(self.request, "Document archivé avec succès.")
        return redirect('ged:document_detail', pk=document.pk)


# =============================================================================
# CONSULTATION DOCUMENT
# =============================================================================

class DocumentDetailView(LoginRequiredMixin, DetailView):
    """Affichage du document + historique."""
    model = DocumentGED
    template_name = 'ged/document_detail.html'
    context_object_name = 'document'

    def dispatch(self, request, *args, **kwargs):
        document = self.get_object()
        if not document.peut_etre_vu_par(request.user):
            return HttpResponseForbidden(
                "Vous n'avez pas les droits pour consulter ce document."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['historique'] = (
            self.object.historique.all()
            .order_by('-date_action')
        )
        return context


# =============================================================================
# LISTE DOCUMENTS
# =============================================================================

class DocumentListView(LoginRequiredMixin, ListView):
    """
    Liste globale GED avec filtrage :
    - confidentialité
    - capacités CORE
    - barrière MDS
    """
    model = DocumentGED
    template_name = 'ged/document_list.html'
    context_object_name = 'documents'
    paginate_by = 25

    def get_queryset(self):
        from .utils import get_documents_for_user
        return (
            get_documents_for_user(self.request.user)
            .select_related('type_document', 'uploaded_by')
        )


# =============================================================================
# TÉLÉCHARGEMENT
# =============================================================================

class DownloadDocumentView(LoginRequiredMixin, View):
    def get(self, request, pk):
        document = get_object_or_404(DocumentGED, pk=pk)

        if not document.peut_etre_vu_par(request.user):
            return HttpResponseForbidden()

        version = document.versions.first()
        if not version:
            messages.error(request, "Aucune version disponible.")
            return redirect("ged:document_detail", pk=document.pk)

        storage = SeaweedFSStorage()
        file_data = storage.open(version.seaweedfs_id)

        document.log_action(
            "TELECHARGEMENT",
            request.user,
            "Téléchargement",
            request,
        )

        return FileResponse(
            file_data,
            as_attachment=True,
            filename=f"{document.titre}.{version.extension}",
        )



# =============================================================================
# MODIFICATION MÉTADONNÉES
# =============================================================================

class DocumentUpdateView(LoginRequiredMixin, UpdateView):
    """Modification des métadonnées GED."""
    model = DocumentGED
    form_class = DocumentGEDForm
    template_name = 'ged/document_form.html'

    def dispatch(self, request, *args, **kwargs):
        document = self.get_object()
        if not document.peut_etre_modifie_par(request.user):
            return HttpResponseForbidden(
                "Droits insuffisants pour modifier ce document."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        document = form.save()
        document.log_action(
            'MODIFICATION',
            self.request.user,
            "Mise à jour des métadonnées",
            self.request,
        )
        messages.success(self.request, "Modifications enregistrées.")
        return redirect('ged:document_detail', pk=document.pk)


# =============================================================================
# SUPPRESSION
# =============================================================================

class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    """
    Suppression LOGIQUE en base.
    La suppression physique SeaweedFS est gérée EXCLUSIVEMENT
    par le signal post_delete.
    """
    model = DocumentGED
    template_name = 'ged/document_confirm_delete.html'
    success_url = reverse_lazy('ged:document_list')

    def dispatch(self, request, *args, **kwargs):
        document = self.get_object()
        if not document.peut_etre_modifie_par(request.user):
            return HttpResponseForbidden(
                "Droits de suppression insuffisants."
            )
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        document = self.get_object()
        logger.info(
            f"GED: Document ID {document.id} supprimé par "
            f"{request.user.username}"
        )
        messages.success(
            request,
            "Document définitivement supprimé."
        )
        return super().delete(request, *args, **kwargs)


# =============================================================================
# VALIDATION (CADRES)
# =============================================================================

def validate_document(request, pk):
    """Validation manuelle réservée à la capacité 'peut_valider'."""
    if request.method != 'POST':
        return HttpResponseForbidden("Requête invalide.")

    document = get_object_or_404(DocumentGED, pk=pk)

    if not request.user.a_la_capacite('peut_valider'):
        return HttpResponseForbidden(
            "Capacité de validation requise."
        )

    document.statut = 'VALIDE'
    document.save()
    document.log_action(
        'VALIDATION',
        request.user,
        "Validation manuelle par cadre",
        request,
    )

    messages.success(
        request,
        "Le document a été validé et archivé."
    )
    return redirect('ged:document_detail', pk=document.pk)


# =============================================================================
# ADMINISTRATION TYPES
# =============================================================================

class DocumentTypeListView(LoginRequiredMixin, ListView):
    model = DocumentType
    template_name = 'ged/admin/type_list.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class DocumentTypeCreateView(LoginRequiredMixin, CreateView):
    model = DocumentType
    fields = '__all__'
    template_name = 'ged/admin/type_form.html'
    success_url = reverse_lazy('ged:document_type_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class DocumentTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = DocumentType
    fields = '__all__'
    template_name = 'ged/admin/type_form.html'
    success_url = reverse_lazy('ged:document_type_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
