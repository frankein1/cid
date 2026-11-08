# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/envoi.py
"""Envoi des dossiers depuis CID : par mail (papier évité) ou imprimé pour un envoi papier ; compteur de pages.

La statistique est collective (« nous avons économisé N pages par rapport aux anciens usages ») : par MDS et pour
le Département, jamais par agent (choix de Fred, 8/11/2026)."""
import io

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMessage
from django.db.models import Count, Sum

from logement.models import EnvoiDossier


def pages_a4(pdf):
    """Pages d'un PDF en équivalent A4 : une page A3 (ou plus grande) compte pour deux."""
    from pypdf import PdfReader
    try:
        n = 0
        for page in PdfReader(io.BytesIO(pdf)).pages:
            l, h = float(page.mediabox.width), float(page.mediabox.height)
            n += 2 if l * h > 600 * 850 * 1.5 else 1
        return n
    except Exception:
        return 0


def contenu_document(doc):
    """(nom de fichier, octets) d'un document de la GED, ou None s'il n'est plus disponible."""
    from ged.storage import SeaweedFSStorage
    version = doc.versions.first()
    fid = version.seaweedfs_id if version else doc.seaweedfs_id
    extension = version.extension if version else doc.extension
    if not fid:
        return None
    try:
        f = SeaweedFSStorage().open(fid)
        octets = f.read()
        f.close()
    except Exception:
        return None
    return f"{doc.titre}.{extension}", octets


def pages_document(doc):
    c = contenu_document(doc)
    if not c:
        return 1
    nom, octets = c
    return (pages_a4(octets) or 1) if nom.lower().endswith('.pdf') else 1


def lettre_mds(mds):
    from mds.models import MDS
    return "MDSP" if mds and mds.type_mds == MDS.PROXIMITE else "MDST"


def objet_mail(mds, intitule, beneficiaire):
    """Ex. « MDST - Port-de-Bouc - Fiche saisine rapport social et justificatifs pour COPP - DUPONT Jeanne »."""
    return (f"{lettre_mds(mds)} - {mds.ville if mds else ''} - {intitule} - "
            f"{beneficiaire.nom.upper()} {beneficiaire.prenom}")


def mail_configure():
    """La messagerie sortante de CID est-elle réglée (variables EMAIL_* sur le serveur) ? Sinon, l'agent envoie
    depuis sa propre messagerie et confirme l'envoi."""
    return 'dummy' not in settings.EMAIL_BACKEND


def enregistrer(obj, nature, mds, mode, pages):
    return EnvoiDossier.objects.create(content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk,
                                       nature=nature, mds=mds, mode=mode, pages=pages)


def envoyer_mail(destinataires, objet, message, pdf, nom_pdf, documents, reply_to=None):
    """Envoie le PDF et les pièces de la GED ; retourne la liste des pièces jointes réellement attachées."""
    m = EmailMessage(subject=objet, body=message, from_email=settings.DEFAULT_FROM_EMAIL, to=destinataires,
                     reply_to=[reply_to] if reply_to else None)
    m.attach(nom_pdf, pdf, 'application/pdf')
    jointes = []
    for doc in documents:
        c = contenu_document(doc)
        if c:
            m.attach(c[0], c[1])
            jointes.append(doc)
    m.send(fail_silently=False)
    return jointes


def papier_evite(mds=None):
    """{'pages_evitees', 'envois_mail', 'envois_imprimes', 'pages_imprimees', 'par_nature': [...], 'par_mds': [...]}"""
    qs = EnvoiDossier.objects.all()
    if mds is not None:
        qs = qs.filter(mds=mds)
    mail = qs.filter(mode=EnvoiDossier.MAIL)
    imp = qs.filter(mode=EnvoiDossier.IMPRIME)
    return {
        'pages_evitees': mail.aggregate(n=Sum('pages'))['n'] or 0,
        'envois_mail': mail.count(),
        'envois_imprimes': imp.count(),
        'pages_imprimees': imp.aggregate(n=Sum('pages'))['n'] or 0,
        'par_nature': list(qs.values('nature', 'mode').annotate(n=Count('id'), pages=Sum('pages')).order_by('nature', 'mode')),
        'par_mds': list(mail.values('mds__nom').annotate(pages=Sum('pages'), n=Count('id')).order_by('-pages')),
    }
