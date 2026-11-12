# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/indigne_rapport.py
"""Note de visite à domicile « lutte contre le mal logement » : texte d'introduction pré-rempli depuis CID, et
feuille A4 (en-tête de la MDS, objet, corps, signature). Document distinct de la fiche PDLHI."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

PHRASE_ORIGINE = {
    'VAD': "la famille {nom} a contacté nos services afin de faire une visite à domicile concernant une suspicion "
           "d'habitat dégradé",
    'LOCATAIRE': "la famille {nom} a signalé à nos services une suspicion d'habitat dégradé dans son logement",
    'BAILLEUR': "le bailleur a signalé à nos services une suspicion d'habitat dégradé concernant le logement de la "
                "famille {nom}",
    'COMMUNE': "la commune a signalé à nos services une suspicion d'habitat dégradé concernant le logement de la "
               "famille {nom}",
    'AUTRE': "un signalement a été transmis à nos services concernant le logement de la famille {nom}",
}
OBJET = "Visite à Domicile, lutte contre le mal logement"


def introduction(s):
    """Texte d'introduction proposé à l'AS ; elle le modifie librement avant signature."""
    nom = s.beneficiaire.nom if s.beneficiaire_id else "[nom de la famille]"
    phrases = [PHRASE_ORIGINE.get(s.origine, PHRASE_ORIGINE['AUTRE']).format(nom=nom) + "."]
    if s.date_saisine:
        phrases.append(f"La MDS a été saisie le {s.date_saisine:%d/%m/%Y}.")
    date_visite = f"{s.creneau.date:%d/%m/%Y}" if s.creneau_id else "[date de la visite]"
    phrases.append(f"Ce rendez-vous a été réalisé le {date_visite} en présence de la famille.")
    return " ".join(phrases) + "\n\nIl ressort de notre visite que :\n> "


def _t(v):
    return escape(str(v or "")).replace("\n", "<br/>")


def note_pdf(s, agent):
    """Feuille A4 : en-tête de la MDS (haut à gauche), objet, corps du rapport, signature."""
    st = getSampleStyleSheet()
    entete = ParagraphStyle('e', parent=st['BodyText'], fontSize=9, leading=11.5)
    corps = ParagraphStyle('c', parent=st['BodyText'], fontSize=10.5, leading=14, spaceAfter=4)
    puce = ParagraphStyle('p', parent=corps, leftIndent=0.8 * cm, bulletIndent=0.3 * cm)
    objet = ParagraphStyle('o', parent=corps, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=12)
    droite = ParagraphStyle('d', parent=corps, alignment=2)

    mds = s.mds
    profils = ", ".join(p.nom for p in agent.profils.all()) if agent else ""
    elements = [
        Paragraph("Département des Bouches-du-Rhône", entete),
        Paragraph("Direction Adjointe à la Solidarité", entete),
        Paragraph("Direction des Territoires et de l'Action Sociale", entete),
        Spacer(1, 8),
        Paragraph(f"Maison départementale de la solidarité : {_t(mds.nom)}", entete),
        Paragraph(f"{_t(mds.adresse)}<br/>{_t(mds.code_postal)} {_t(mds.ville)}", entete),
        Spacer(1, 6),
        Paragraph(f"Agent : {_t(agent.get_full_name() or agent.username) if agent else '—'}"
                  + (f"<br/>{_t(profils)}" if profils else ""), entete),
        Paragraph(f"{_t(mds.ville)}, le {s.vad_date_signature:%d/%m/%Y}" if s.vad_signee
                  else f"{_t(mds.ville)}, le {s.date_creation:%d/%m/%Y}", droite),
        Paragraph(f"Objet : {_t(OBJET)}", objet),
    ]
    for ligne in (s.rapport_vad or "").split("\n"):
        ligne = ligne.rstrip()
        if not ligne.strip():
            elements.append(Spacer(1, 6))
        elif ligne.lstrip().startswith(">"):
            elements.append(Paragraph(_t(ligne.lstrip()[1:].strip()), puce, bulletText="•"))
        else:
            elements.append(Paragraph(_t(ligne), corps))
    elements.append(Spacer(1, 24))
    if s.vad_signee:
        elements.append(Paragraph(f"{_t(s.vad_signee_par.get_full_name() or s.vad_signee_par.username)}<br/>"
                                  f"Signé le {s.vad_date_signature:%d/%m/%Y}", droite))
    else:
        elements.append(Paragraph("Non signé.", droite))
    buf = BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=1.8 * cm,
                      bottomMargin=1.8 * cm, title=OBJET).build(elements)
    return buf.getvalue()
