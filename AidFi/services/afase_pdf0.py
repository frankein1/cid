#/AidFi/services/afase_pdf.py

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO


def generer_pdf_afase(demande):
    buffer = BytesIO()
    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(buffer)
    story = []

    story.append(Paragraph(
    f"<b>Demande AFASE</b><br/>"
    f"Bénéficiaire : {demande.beneficiaire}<br/>"
    f"Montant sollicité : {demande.montant_demande} €<br/>"
    f"Durée : {demande.duree_demande} mois",
    styles["Normal"]
))

    if hasattr(demande, "decision"):
    story.append(Paragraph(
        f"<br/><b>Décision :</b> {demande.decision.get_type_decision_display()}<br/>"
        f"Code : {demande.decision.code_decision}<br/>"
        f"Montant accordé : {demande.decision.montant_accorde} €",
        styles["Normal"]
    ))


    doc.build(story)
    buffer.seek(0)
    return buffer
