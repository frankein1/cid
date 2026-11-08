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

from ..models import (DemandeFSL, DestinataireExpulsion, DiagnosticExpulsion, DossierExpulsion, EnvoiDossier,
                      PassageCommission, SaisineCOPP)
from ..services import circuit, copp, envoi
from ..services.fsl_pdf import dossier as dossier_fsl


class _Dossier:
    """Ce qu'il faut savoir d'un dossier pour l'envoyer, quelle que soit sa nature : FSL, COPP, et pour la
    prévention des expulsions le DSF (ou bordereau de carence) et le questionnaire au bailleur."""
    def __init__(self, nature, obj):
        self.nature, self.obj = nature, obj
        self.b, self.mds = obj.beneficiaire, obj.mds
        self.destinataires_proposes = []
        if nature == 'fsl':
            self.libelle = f"FSL {obj.get_type_aide_display().lower()}"
            self.intitule = f"Demande FSL {obj.get_type_aide_display().lower()} et justificatifs"
            self.retour = reverse('logement:fsl_detail', args=[obj.pk])
            self.envoyable = obj.statut in (DemandeFSL.VALIDEE, DemandeFSL.AJOURNEE)
            self.pourquoi = "La demande part avec le visa du cadre : demandez-le d'abord."
            self.pieces_proposees = []
        elif nature == 'copp':
            self.libelle = "COPP"
            self.intitule = "Fiche saisine rapport social et justificatifs pour COPP"
            self.retour = reverse('logement:copp_detail', args=[obj.pk])
            self.envoyable = obj.statut == SaisineCOPP.BROUILLON and bool(obj.motifs) and bool(obj.rapport_social)
            self.pourquoi = "Indiquez au moins un motif et rédigez le rapport social avant l'envoi."
            self.pieces_proposees = list(obj.pieces.all())
        elif nature == 'dsf':
            dossier = obj.dossier
            carence = obj.type_document == DiagnosticExpulsion.CARENCE
            self.libelle = "Bordereau de carence" if carence else "DSF"
            audience = f" – audience du {dossier.date_audience:%d/%m/%Y}" if dossier.date_audience else ""
            self.intitule = ("Bordereau de carence" if carence else "Diagnostic social et financier") + audience
            self.retour = reverse('logement:diagnostic_detail', args=[obj.pk])
            self.envoyable = obj.statut in (DiagnosticExpulsion.VISE, DiagnosticExpulsion.ENVOYE)
            self.pourquoi = "Le document part avec le visa du cadre : demandez-le d'abord."
            self.pieces_proposees = []
            self.destinataires_proposes = DestinataireExpulsion.pour(dossier.mds)
            self.nom_personne = dossier.nom_complet
        elif nature == 'actualisation':
            from types import SimpleNamespace
            com = obj.commission
            self.libelle = "Actualisation"
            self.intitule = f"Actualisation pour la {com.get_type_commission_display().lower()} du {com.date:%d/%m/%Y}"
            self.retour = reverse('logement:passage_detail', args=[obj.pk])
            self.envoyable = obj.statut in (PassageCommission.VISEE, PassageCommission.TRANSMISE)
            self.pourquoi = "L'actualisation part avec le visa du cadre : demandez-le d'abord."
            self.pieces_proposees = []
            self.destinataires_proposes = [SimpleNamespace(nom=f"secrétariat – {com.nom}", email=com.email)] \
                if com.email else []
            self.nom_personne = obj.dossier.nom_complet
        else:                                                  # 'bailleur'
            self.libelle = "Questionnaire bailleur"
            self.intitule = "Questionnaire bailleur pour le diagnostic social et financier"
            self.retour = reverse('logement:expulsion_detail', args=[obj.pk])
            self.envoyable = bool(obj.questionnaire_retour_avant)
            self.pourquoi = "Indiquez d'abord la date de retour souhaitée."
            self.pieces_proposees = []
            self.nom_personne = obj.nom_complet
        if self.b is not None:
            self.nom_personne = f"{self.b.nom.upper()} {self.b.prenom}"

    def peut_envoyer(self, user):
        if self.nature in ('dsf', 'bailleur', 'actualisation'):
            from ..services.expulsion import peut_ecrire
            dossier = self.obj if self.nature == 'bailleur' else self.obj.dossier
            return peut_ecrire(user, dossier) and not (dossier.mds_id is None)
        return user_peut_agir_sur_beneficiaire(user, self.b) and self.b.niveau_acces(user) == 'complet'

    def pdf(self):
        if self.nature == 'fsl':
            return dossier_fsl(self.obj)[0]
        if self.nature == 'copp':
            return copp.dossier(self.obj)[0]
        from ..services import expulsion_documents as E
        if self.nature == 'actualisation':
            from ..services.commissions import actualisation_pdf
            return actualisation_pdf(self.obj)
        if self.nature == 'dsf':
            return E.document(self.obj)
        return E.questionnaire_pdf(self.obj, self.obj.questionnaire_retour_avant)

    def nom_pdf(self):
        return f"{self.libelle.replace(' ', '_')}_{self.nom_personne.replace(' ', '_')}.pdf"

    def marquer_envoye(self, user, mode):
        if self.nature == 'fsl':
            circuit.envoyer(self.obj, user, mode=mode)
        elif self.nature == 'copp':
            self.obj.statut = SaisineCOPP.ENVOYEE
            self.obj.tracer(user, "Envoyée à la commission" + (" par mail" if mode == 'MAIL' else " (imprimée)"),
                            str(self.obj.commission or ""))
            self.obj.save()
        elif self.nature == 'dsf':
            from ..services.expulsion_mds import marquer_transmis
            marquer_transmis(self.obj, user, mode)
        elif self.nature == 'actualisation':
            from ..services.commissions import marquer_transmis
            marquer_transmis(self.obj, user, mode)
        else:
            from ..services.expulsion_mds import questionnaire_envoye
            questionnaire_envoye(self.obj, user, self.obj.questionnaire_retour_avant)


def _documents_usager(b, user):
    from beneficiaire.models import Beneficiaire
    from ged.utils import get_documents_for_user
    return list(get_documents_for_user(user).filter(content_type=ContentType.objects.get_for_model(Beneficiaire),
                                                     object_id=b.pk).select_related('type_document')
                .order_by('-date_creation').distinct()[:60])


def _charger(request, nature, pk):
    if nature == 'dsf':
        return _Dossier(nature, get_object_or_404(DiagnosticExpulsion.objects.select_related('dossier__mds'), pk=pk))
    if nature == 'bailleur':
        return _Dossier(nature, get_object_or_404(DossierExpulsion.objects.select_related('mds', 'beneficiaire'), pk=pk))
    if nature == 'actualisation':
        return _Dossier(nature, get_object_or_404(PassageCommission.objects.select_related('dossier__mds', 'commission'),
                                                  pk=pk))
    modele = {'fsl': DemandeFSL, 'copp': SaisineCOPP}.get(nature)
    if not modele:
        return None
    obj = get_object_or_404(modele.objects.select_related('beneficiaire', 'mds'), pk=pk)
    return _Dossier(nature, obj)


@login_required
def envoi_dossier(request, nature, pk):
    dos = _charger(request, nature, pk)
    if dos is None or not dos.peut_envoyer(request.user):
        return HttpResponseForbidden("Réservé aux agents de la MDS de l'usager.")
    if not dos.envoyable and request.POST.get('action') != 'mail_confirme':
        messages.error(request, dos.pourquoi)
        return redirect(dos.retour)
    docs_usager = _documents_usager(dos.b, request.user) if dos.b else []
    objet = envoi.objet_mail(dos.mds, dos.intitule, dos.nom_personne)
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
        'destinataires': ", ".join(x.email for x in dos.destinataires_proposes),
        'message': (f"Bonjour,\n\nVeuillez trouver ci-joint le dossier de {dos.nom_personne} "
                    f"({dos.intitule.lower()}).\n\nCordialement,\n"
                    f"{request.user.get_full_name()}\n{dos.mds.nom if dos.mds else ''}"),
        'pdf_url': _url_pdf(dos),
    })


def _url_pdf(dos):
    nom = {'fsl': 'logement:fsl_pdf', 'copp': 'logement:copp_pdf', 'dsf': 'logement:diagnostic_pdf',
           'bailleur': 'logement:questionnaire_pdf', 'actualisation': 'logement:passage_pdf'}[dos.nature]
    return reverse(nom, args=[dos.obj.pk])


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
