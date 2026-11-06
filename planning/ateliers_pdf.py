# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# planning/ateliers_pdf.py
"""Feuille d'émargement d'une séance d'atelier collectif (à imprimer et faire signer)."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles


def emargement_pdf(s, inscrits):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=3 * cm,
                            bottomMargin=2 * cm, title="Feuille d'émargement")
    st = get_ditas_styles()
    infos = (f"{s.date:%d/%m/%Y}, de {s.heure_debut:%H:%M} à {s.heure_fin:%H:%M} — {escape(s.lieu or s.mds.nom)}"
             + (f" — animé par {escape(s.animateur)}" if s.animateur else ""))
    el = [Paragraph(f"<b>Feuille d'émargement — {escape(s.titre)}</b>", st["Normal"]), Spacer(1, 0.2 * cm),
          Paragraph(infos, st["Normal"]), Spacer(1, 0.5 * cm)]
    lignes = [["", "Nom et prénom", "Signature"]] + [[str(i), p.nom_complet, ""] for i, p in enumerate(inscrits, 1)]
    lignes += [[str(len(inscrits) + i), "", ""] for i in range(1, 4)]          # lignes libres
    t = Table(lignes, colWidths=[1 * cm, 9 * cm, 7.5 * cm], rowHeights=[0.7 * cm] + [1.0 * cm] * (len(lignes) - 1))
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("FONTSIZE", (0, 0), (-1, -1), 10)]))
    el.append(t)
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer
