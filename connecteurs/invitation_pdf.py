# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/invitation_pdf.py
"""
Courrier d'invitation à prendre en ligne le RDV de renouvellement du contrat RSA, avec le lien personnel en
QR code. Texte modifiable en administration (Modèles de courriers → RSA_INVITATION_RDV).
"""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table

from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles
from insertion.services.contrat_pdf import _bloc_mds, _d, _doc, _valeurs_communes

from .models import MotifRDVSP


def _qr(texte, taille=4.2 * cm):
    w = QrCodeWidget(texte)
    x1, y1, x2, y2 = w.getBounds()
    d = Drawing(taille, taille, transform=[taille / (x2 - x1), 0, 0, taille / (y2 - y1), 0, 0])
    d.add(w)
    return d


def courrier_invitation_pdf(inv):
    from django.utils import timezone

    from core.courriers import modele_texte, rendu
    c, b = inv.contrat, inv.beneficiaire
    motif = MotifRDVSP.objects.filter(actif=True).first()
    valeurs = {**(_valeurs_communes(c) if c else {"civilite_appel": "Madame, Monsieur",
                                                   "beneficiaire": f"{b.prenom} {b.nom.upper()}"}),
               "date_fin": _d(c.date_fin) if c else "", "lien": inv.lien or "(lien délivré à l'envoi)",
               "delai_min": str(motif.delai_min_heures if motif else 48),
               "delai_max": str(motif.delai_max_jours if motif else 15)}
    st = get_ditas_styles()
    m = modele_texte("RSA_INVITATION_RDV")
    buffer = BytesIO()
    doc = _doc(buffer, "Invitation à prendre rendez-vous")
    adresse = f"{escape(b.get_civilite_display() if hasattr(b, 'get_civilite_display') else '')} " \
              f"{escape(b.prenom)} {escape(b.nom.upper())}<br/>{escape(b.adresse or '')}<br/>" \
              f"{escape(b.code_postal or '')} {escape(b.ville or '')}"
    el = [Paragraph(_bloc_mds(c) if c else "", st["Normal"]), Spacer(1, 0.5 * cm),
          Table([["", Paragraph(adresse, st["Normal"])]], colWidths=[9 * cm, 8 * cm]), Spacer(1, 0.8 * cm),
          Paragraph(f"{escape(c.mds.ville if c and c.mds else '')}, le {_d(timezone.localdate())}", st["Normal"]),
          Spacer(1, 0.4 * cm),
          Paragraph(f"<b>Objet :</b> {rendu.ligne(m['objet'], valeurs, {})}", st["Normal"]), Spacer(1, 0.5 * cm)]
    for para in rendu.paragraphes(m["corps"], valeurs, {}):
        el += [Paragraph(para, st["Normal"]), Spacer(1, 0.3 * cm)]
    if inv.lien:
        el += [Spacer(1, 0.2 * cm), Table([[_qr(inv.lien)]], colWidths=[17 * cm]), Spacer(1, 0.3 * cm)]
    el += [Spacer(1, 0.4 * cm), Table([["", Paragraph(rendu.bloc(m["signature"], valeurs, {}), st["Normal"])]],
                                      colWidths=[9 * cm, 8 * cm])]
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer
