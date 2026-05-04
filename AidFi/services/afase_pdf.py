from io import BytesIO
import os

from django.conf import settings
from django.utils import timezone

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import cm

from AidFi.models.m_afase import DemandeAFASE

LOGO_PATH = os.path.join(settings.BASE_DIR, "static/img/logoCD13.png")


def get_ditas_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TitreOfficiel",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=16,
        leading=20,
        spaceAfter=20,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading2"],
        fontSize=12,
        leading=14,
        color=colors.blue,
        spaceBefore=15,
        spaceAfter=10,
        fontName="Helvetica-Bold",
        underline=True,
    ))
    styles.add(ParagraphStyle(
        name="DataLabel",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
    ))
    return styles


def draw_page_template(canvas, doc):
    canvas.saveState()

    if os.path.exists(LOGO_PATH):
        try:
            canvas.drawImage(
                LOGO_PATH,
                x=1.5 * cm,
                y=A4[1] - 3 * cm,
                width=5 * cm,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    canvas.setLineWidth(0.5)
    canvas.line(1.5 * cm, A4[1] - 3.2 * cm, A4[0] - 1.5 * cm, A4[1] - 3.2 * cm)

    canvas.setFont("Helvetica", 8)
    date_gen = timezone.now().strftime("%d/%m/%Y à %H:%M")
    canvas.drawString(1.5 * cm, 1 * cm, f"SI DITAS - Document Officiel - Généré le {date_gen}")
    canvas.drawRightString(A4[0] - 1.5 * cm, 1 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _money(value):
    try:
        return f"{float(value):.2f} €"
    except Exception:
        return "0.00 €"


def generer_pdf_afase(demande: DemandeAFASE):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=3.5 * cm,
        bottomMargin=2 * cm,
    )
    elements = []
    styles = get_ditas_styles()

    benef = demande.beneficiaire
    evaluation = getattr(demande, "evaluation_afase", None)
    budget = getattr(demande, "budget", None)
    decision = getattr(demande, "decision", None)

    elements.append(Paragraph("DEMANDE D'AIDE FINANCIÈRE AFASE", styles["TitreOfficiel"]))

    info_dossier = [
        [
            Paragraph(f"<b>Dossier ID :</b> {demande.id}", styles["Normal"]),
            Paragraph(
                f"<b>Date :</b> {demande.date_creation.strftime('%d/%m/%Y') if getattr(demande, 'date_creation', None) else '-'}",
                styles["Normal"],
            ),
        ]
    ]
    elements.append(Table(info_dossier, colWidths=[9 * cm, 9 * cm]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("I. IDENTITÉ DU BÉNÉFICIAIRE", styles["SectionHeader"]))
    data_identite = [
        ["Nom de famille :", (benef.nom or "").upper()],
        ["Prénom :", benef.prenom or ""],
        ["Date de naissance :", benef.date_naissance.strftime("%d/%m/%Y") if benef.date_naissance else "Non renseignée"],
        ["N° GENESIS :", demande.numero_genesis or "Néant"],
        ["Code interne :", getattr(benef, "code_interne", None) or "N/C"],
    ]
    t_identite = Table(data_identite, colWidths=[5 * cm, 13 * cm])
    t_identite.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.2, colors.lightgrey),
    ]))
    elements.append(t_identite)

    elements.append(Paragraph("II. CONTEXTE ET ÉVALUATION", styles["SectionHeader"]))
    elements.append(Paragraph(f"<b>Avis du travailleur social :</b> {demande.get_avis_ts_display()}", styles["Normal"]))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph("<b>Code instruction :</b>", styles["DataLabel"]))
    elements.append(Paragraph(getattr(evaluation, "code_instruction", "") or "Non renseigné", styles["Normal"]))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph("<b>Analyse de la situation :</b>", styles["DataLabel"]))
    elements.append(Paragraph(getattr(evaluation, "analyse_problematique", "") or "Aucune analyse détaillée fournie.", styles["Normal"]))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph("<b>Justification de la demande :</b>", styles["DataLabel"]))
    elements.append(Paragraph(getattr(evaluation, "justification_demande", "") or "Néant.", styles["Normal"]))

    elements.append(Paragraph("III. ÉLÉMENTS BUDGÉTAIRES (MENSUELS)", styles["SectionHeader"]))

    def format_budget_table(data_dict):
        if not data_dict:
            return Paragraph("Aucune donnée.", styles["Normal"])
        rows = []
        for k, v in data_dict.items():
            try:
                val = f"{float(v):.2f} €"
            except Exception:
                val = str(v)
            rows.append(f"• {k} : {val}")
        return Paragraph("<br/>".join(rows), styles["Normal"])

    data_budget = [
        [Paragraph("<b>RESSOURCES</b>", styles["Normal"]), Paragraph("<b>CHARGES</b>", styles["Normal"])],
        [
            format_budget_table(getattr(budget, "ressources", None)),
            format_budget_table(getattr(budget, "charges", None)),
        ],
    ]
    t_budget = Table(data_budget, colWidths=[9 * cm, 9 * cm])
    t_budget.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (1, 0), colors.whitesmoke),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_budget)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Reste à vivre journalier :</b> {_money(getattr(budget, 'reste_a_vivre', 0))} / jour", styles["Normal"]))

    elements.append(Paragraph("IV. DEMANDE FINANCIÈRE", styles["SectionHeader"]))
    elements.append(Paragraph(f"Montant sollicité : <b>{_money(demande.montant_sollicite)}</b>", styles["Normal"]))
    elements.append(Paragraph(f"Durée demandée : {demande.duree_demande or 0} mois", styles["Normal"]))

    if decision:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("V. DÉCISION ADMINISTRATIVE", styles["SectionHeader"]))
        data_dec = [
            ["Type de décision :", decision.get_type_decision_display()],
            ["Code de décision :", decision.code_decision or "-"],
            ["Libellé :", decision.libelle_decision or "-"],
            ["Montant accordé :", _money(decision.montant_accorde)],
            ["Durée accordée :", f"{decision.duree_accordee or 0} mois"],
            ["Date de commission :", decision.date_decision.strftime("%d/%m/%Y") if decision.date_decision else "-"],
            ["Observations :", Paragraph(decision.motivation or "-", styles["Normal"])],
        ]
        t_dec = Table(data_dec, colWidths=[5 * cm, 13 * cm])
        t_dec.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.2, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(t_dec)

    doc.build(elements, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer
