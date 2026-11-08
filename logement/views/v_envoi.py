# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/views/v_envoi.py
"""« Envoi par mail » ou « Imprimer pour envoi » d'un dossier (FSL, COPP) : un PDF d'abord, le papier seulement
si le destinataire l'exige ; chaque envoi alimente le compteur de papier évité (collectif, jamais par agent)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from beneficiaire.views import user_peut_agir_sur_beneficiaire

from ..models import DemandeFSL, EnvoiDossier, SaisineCOPP
from ..services import circuit, copp, envoi
from ..services.fsl_pdf import dossier as dossier_fsl


class _Dossier:
    """Ce qu'il faut savoir d'un dossier pour l'envoyer, quelle que soit sa nature."""
    def __init__(self, nature, obj):
        self.nature, self.obj, self.b, self.mds = nature, obj, obj.beneficiaire, obj.mds
        if nature == 'fsl':
            self.libelle = f"FSL {obj.get_type_aide_display().lower()}"
            self.intitule = f"Demande FSL {obj.get_type_aide_display().lower()} et justificatifs"
            self.retour = reverse('logement:fsl_detail', args=[obj.pk])
            self.envoyable = obj.statut in (DemandeFSL.VALIDEE, DemandeFSL.AJOURNEE)
            self.pourquoi = "La demande part avec le visa du cadre : demandez-le d'abord."
            self.pieces_proposees = []
        else:
            self.libelle = "COPP"
            self.intitule = "Fiche saisine rapport social et justificatifs pour COPP"
            self.retour = reverse('logement:copp_detail', args=[obj.pk])
            self.envoyable = obj.statut == SaisineCOPP.BROUILLON and bool(obj.motifs) and bool(obj.rapport_social)
            self.pourquoi = "Indiquez au moins un motif et rédigez le rapport social avant l'envoi."
            self.pieces_proposees = list(obj.pieces.all())

    def pdf(self):
        if self.nature == 'fsl':
            return dossier_fsl(self.obj)[0]
        return copp.dossier(self.obj)[0]

    def nom_pdf(self):
        return f"{self.libelle.replace(' ', '_')}_{self.b.nom.upper()}_{self.b.prenom}.pdf"

    def marquer_envoye(self, user, mode):
        if self.nature == 'fsl':
            circuit.envoyer(self.obj, user, mode=mode)
        else:
            self.obj.statut = SaisineCOPP.ENVOYEE
            self.obj.tracer(user, "Envoyée à la commission" + (" par mail" if mode == 'MAIL' else " (imprimée)"),
                            str(self.obj.commission or ""))
            self.obj.save()


def _documents_usager(b, user):
    from beneficiaire.models import Beneficiaire
    from ged.utils import get_documents_for_user
    return list(get_documents_for_user(user).filter(content_type=ContentType.objects.get_for_model(Beneficiaire),
                                                     object_id=b.pk).select_related('type_document')
                .order_by('-date_creation').distinct()[:60])


def _charger(request, nature, pk):
    modele = {'fsl': DemandeFSL, 'copp': SaisineCOPP}.get(nature)
    if not modele:
        return None
    obj = get_object_or_404(modele.objects.select_related('beneficiaire', 'mds'), pk=pk)
    return _Dossier(nature, obj)


@login_required
def envoi_dossier(request, nature, pk):
    dos = _charger(request, nature, pk)
    if dos is None or not user_peut_agir_sur_beneficiaire(request.user, dos.b) or dos.b.niveau_acces(request.user) != 'complet':
        return HttpResponseForbidden("Réservé aux agents de la MDS de l'usager.")
    if not dos.envoyable and request.POST.get('action') != 'mail_confirme':
        messages.error(request, dos.pourquoi)
        return redirect(dos.retour)
    docs_usager = _documents_usager(dos.b, request.user)
    objet = envoi.objet_mail(dos.mds, dos.intitule, dos.b)
    if request.method == 'POST':
        action = request.POST.get('action')
        ids = {int(x) for x in request.POST.getlist('pieces') if x.isdigit()}
        joints = [d for d in docs_usager if d.pk in ids]
        pdf = dos.pdf()
        pages = envoi.pages_a4(pdf) + sum(envoi.pages_document(d) for d in joints)
        if action == 'imprimer':
            dos.marquer_envoye(request.user, EnvoiDossier.IMPRIME)
            envoi.enregistrer(dos.obj, dos.libelle, dos.mds, EnvoiDossier.IMPRIME, pages)
            messages.success(request, f"Envoi papier enregistré ({pages} pages). Le PDF s'ouvre pour l'impression.")
            return redirect(dos.retour + "?imprimer=1")
        if action == 'mail_confirme':
            if dos.envoyable:
                dos.marquer_envoye(request.user, EnvoiDossier.MAIL)
            envoi.enregistrer(dos.obj, dos.libelle, dos.mds, EnvoiDossier.MAIL, int(request.POST.get('pages') or pages))
            messages.success(request, "Envoi par mail enregistré : merci pour le papier économisé.")
            return redirect(dos.retour)
        if action == 'mail':
            destinataires = [x.strip() for x in (request.POST.get('destinataire') or '').replace(';', ',').split(',')
                             if x.strip()]
            if not destinataires:
                messages.error(request, "Indiquez l'adresse du destinataire.")
            elif not envoi.mail_configure():
                # Messagerie sortante de CID non réglée : l'agent envoie depuis sa messagerie, puis confirme
                return render(request, 'logement/envoi_manuel.html', {
                    'dos': dos, 'objet': request.POST.get('objet') or objet, 'destinataires': ", ".join(destinataires),
                    'pages': pages, 'joints': joints, 'pdf_url': _url_pdf(dos)})
            else:
                try:
                    envoi.envoyer_mail(destinataires, request.POST.get('objet') or objet,
                                       request.POST.get('message') or "", pdf, dos.nom_pdf(), joints,
                                       reply_to=dos.mds.email if dos.mds else None)
                except Exception as e:                                       # noqa: BLE001
                    messages.error(request, f"L'envoi a échoué : {e}")
                else:
                    dos.marquer_envoye(request.user, EnvoiDossier.MAIL)
                    envoi.enregistrer(dos.obj, dos.libelle, dos.mds, EnvoiDossier.MAIL, pages)
                    messages.success(request, f"Dossier envoyé par mail à {', '.join(destinataires)} ({pages} pages "
                                              f"non imprimées).")
                    return redirect(dos.retour)
    return render(request, 'logement/envoi.html', {
        'dos': dos, 'objet': objet, 'docs_usager': docs_usager,
        'proposes': {d.pk for d in dos.pieces_proposees}, 'mail_configure': envoi.mail_configure(),
        'message': (f"Bonjour,\n\nVeuillez trouver ci-joint le dossier de {dos.b.prenom} {dos.b.nom.upper()} "
                    f"({dos.intitule.lower()}).\n\nCordialement,\n"
                    f"{request.user.get_full_name()}\n{dos.mds.nom if dos.mds else ''}"),
        'pdf_url': _url_pdf(dos),
    })


def _url_pdf(dos):
    return reverse('logement:fsl_pdf' if dos.nature == 'fsl' else 'logement:copp_pdf', args=[dos.obj.pk])


@login_required
def papier_economise(request):
    """Statistique collective : par MDS et pour le Département. Jamais par agent."""
    from mds.models import MDS
    mds_id = request.GET.get('mds')
    mds = MDS.objects.filter(pk=mds_id).first() if mds_id and mds_id.isdigit() else None
    stats = envoi.papier_evite(mds)
    return render(request, 'logement/papier.html', {
        'stats': stats, 'mds_choisie': mds, 'liste_mds': MDS.objects.filter(active=True).order_by('nom'),
        'ramettes': round(stats['pages_evitees'] / 500, 1), 'kilos': round(stats['pages_evitees'] * 5 / 1000, 1),
    })
