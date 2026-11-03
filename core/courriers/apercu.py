# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/courriers/apercu.py
"""Aperçu PDF d'un modèle de courrier, avec les valeurs d'exemple du registre (aucune donnée réelle)."""
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles
from core.courriers import rendu
from core.courriers.registre import COURRIERS, exemple


def apercu_pdf(code, textes):
    d = COURRIERS[code]
    valeurs, conditions = exemple(code)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=3.5 * cm,
                            bottomMargin=2 * cm, title=f"Aperçu – {d['libelle']}", author="CID")
    st = get_ditas_styles()
    n = st["Normal"]
    el = [Paragraph("<font color='#b91c1c'><b>APERÇU – données d'exemple, toutes les conditions vraies</b></font>", n),
          Spacer(1, 0.3 * cm),
          Paragraph("<b>MDS Exemple</b><br/>1 rue de l'Exemple<br/>13000 Exemple", n), Spacer(1, 0.5 * cm),
          Table([["", Paragraph("Madame Prénom EXEMPLE<br/>2 avenue de l'Exemple<br/>13000 Exemple", n)]],
                colWidths=[9 * cm, 8 * cm]), Spacer(1, 0.8 * cm),
          Paragraph("Exemple, le 01/01/2026", n), Spacer(1, 0.4 * cm),
          Paragraph(f"<b>Objet :</b> {rendu.ligne(textes.get('objet', ''), valeurs, conditions)}", n),
          Spacer(1, 0.5 * cm)]
    for p in rendu.paragraphes(textes.get("corps", ""), valeurs, conditions):
        el += [Paragraph(p, n), Spacer(1, 0.3 * cm)]
    signature = rendu.bloc(textes.get("signature", ""), valeurs, conditions) if "signature" in d else \
        "<i>(signatures des professionnels, ajoutées par CID)</i>"
    el += [Spacer(1, 0.6 * cm), Table([["", Paragraph(signature, n)]], colWidths=[9 * cm, 8 * cm])]
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer
