# AidFi/services/afase_pdf.py

from io import BytesIO
import os
from django.conf import settings
from django.utils import timezone

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import cm

from AidFi.models.m_afase import DemandeAFASE

# ---------------------------------------------------------------------
# CONFIGURATION & CHEMINS
# ---------------------------------------------------------------------
LOGO_PATH = os.path.join(settings.BASE_DIR, "static/img/logoCD13.png")

def get_ditas_styles():
    styles = getSampleStyleSheet()
    # Style Titre Principal
    styles.add(ParagraphStyle(
        name='TitreOfficiel',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=16,
        leading=20,
        spaceAfter=20,
        fontName='Helvetica-Bold'
    ))
    # Style Section
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        leading=14,
        color=colors.blue,
        spaceBefore=15,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        underline=True
    ))
    # Style Donnée (Label: Valeur)
    styles.add(ParagraphStyle(
        name='DataLabel',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold'
    ))
    return styles

# ---------------------------------------------------------------------
# DRAW OVERLAYS (En-tête et Pied de page)
# ---------------------------------------------------------------------
def draw_page_template(canvas, doc):
    canvas.saveState()
    # Logo CD13
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
    
    # Ligne de séparation haut
    canvas.setLineWidth(0.5)
    canvas.line(1.5 * cm, A4[1] - 3.2 * cm, A4[0] - 1.5 * cm, A4[1] - 3.2 * cm)

    # Pied de page
    canvas.setFont('Helvetica', 8)
    date_gen = timezone.now().strftime('%d/%m/%Y à %H:%M')
    canvas.drawString(1.5 * cm, 1 * cm, f"SI DITAS - Document Officiel - Généré le {date_gen}")
    canvas.drawRightString(A4[0] - 1.5 * cm, 1 * cm, f"Page {doc.page}")
    canvas.restoreState()

# ---------------------------------------------------------------------
# FONCTION DE GÉNÉRATION
# ---------------------------------------------------------------------
def generer_pdf_afase(demande: DemandeAFASE):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=3.5*cm, bottomMargin=2*cm
    )
    
    styles = get_ditas_styles()
    elements = []
    benef = demande.beneficiaire

    # --- 1. TITRE ET RÉFÉRENCES ---
    elements.append(Paragraph("DEMANDE D'AIDE FINANCIÈRE AFASE", styles['TitreOfficiel']))
    
    info_dossier = [
        [Paragraph(f"<b>Dossier ID :</b> {demande.id}", styles['Normal']), 
         Paragraph(f"<b>Date :</b> {demande.date_creation.strftime('%d/%m/%Y')}", styles['Normal'])]
    ]
    t_info = Table(info_dossier, colWidths=[9*cm, 9*cm])
    elements.append(t_info)
    elements.append(Spacer(1, 10))

    # --- 2. IDENTITÉ DU BÉNÉFICIAIRE ---
    elements.append(Paragraph("I. IDENTITÉ DU BÉNÉFICIAIRE", styles['SectionHeader']))
    
    data_identite = [
        ["Nom de famille :", benef.nom.upper()],
        ["Prénom :", benef.prenom],
        ["Date de naissance :", benef.date_naissance.strftime('%d/%m/%Y') if benef.date_naissance else "Non renseignée"],
        ["N° GENESIS :", demande.numero_genesis or "Néant"],
        ["Code Interne :", benef.code_interne or "N/C"]
    ]
    
    t_identite = Table(data_identite, colWidths=[5*cm, 13*cm])
    t_identite.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.2, colors.lightgrey),
    ]))
    elements.append(t_identite)

    # --- 3. ÉVALUATION ET CONTEXTE ---
    elements.append(Paragraph("II. CONTEXTE ET ÉVALUATION", styles['SectionHeader']))
    elements.append(Paragraph(f"<b>Avis du Travailleur Social :</b> {demande.get_avis_ts_display()}", styles['Normal']))
    elements.append(Spacer(1, 5))
    
    elements.append(Paragraph("<b>Analyse de la situation :</b>", styles['DataLabel']))
    elements.append(Paragraph(demande.analyse_problematique or "Aucune analyse détaillée fournie.", styles['Normal']))
    elements.append(Spacer(1, 5))
    
    elements.append(Paragraph("<b>Justification de la demande :</b>", styles['DataLabel']))
    elements.append(Paragraph(demande.justification_demande or "Néant.", styles['Normal']))

    # --- 4. BUDGET ET FINANCES ---
    elements.append(Paragraph("III. ÉLÉMENTS BUDGÉTAIRES (MENSUELS)", styles['SectionHeader']))
    
    def format_budget_table(data_dict):
        if not data_dict: return "Aucune donnée."
        rows = []
        for k, v in data_dict.items():
            try:
                val = f"{float(v):.2f} €"
            except:
                val = str(v)
            rows.append(f"• {k} : {val}")
        return Paragraph("<br/>".join(rows), styles['Normal'])

    data_budget = [
        [Paragraph("<b>RESSOURCES</b>", styles['Normal']), Paragraph("<b>CHARGES</b>", styles['Normal'])],
        [format_budget_table(demande.ressources), format_budget_table(demande.charges)]
    ]
    
    t_budget = Table(data_budget, colWidths=[9*cm, 9*cm])
    t_budget.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (1,0), colors.whitesmoke),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_budget)
    
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Reste à vivre journalier :</b> {demande.reste_a_vivre or 0:.2f} € / jour", styles['Normal']))

    # --- 5. OBJET DE LA DEMANDE ---
    elements.append(Paragraph("IV. DEMANDE FINANCIÈRE", styles['SectionHeader']))
    elements.append(Paragraph(f"Montant sollicité : <b>{demande.montant_sollicite:.2f} €</b>", styles['Normal']))
    elements.append(Paragraph(f"Durée prévue : {demande.duree_demande} mois", styles['Normal']))

    # --- 6. DÉCISION (SI DISPONIBLE) ---
    if hasattr(demande, 'decision') and demande.decision:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("V. DÉCISION ADMINISTRATIVE", styles['SectionHeader']))
        dec = demande.decision
        
        data_dec = [
            ["Type de décision :", dec.get_type_decision_display()],
            ["Montant accordé :", f"{dec.montant_accorde or 0:.2f} €"],
            ["Date de commission :", dec.date_decision.strftime('%d/%m/%Y') if dec.date_decision else "-"],
            ["Observations :", Paragraph(dec.libelle_decision or "-", styles['Normal'])]
        ]
        
        t_dec = Table(data_dec, colWidths=[5*cm, 13*cm])
        t_dec.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.2, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        elements.append(t_dec)

    # Construction du document
    doc.build(elements, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer
