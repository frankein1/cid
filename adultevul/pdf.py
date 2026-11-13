# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# adultevul/pdf.py
"""Annexes de la procédure adultes vulnérables (note MDS n°19), générées depuis les données de CID.
Les annexes sont signées à la main après impression : les zones de signature restent vides."""
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import ELEMENTS, PROPOSITIONS

BLEU = colors.HexColor("#1476a8")
GRIS = colors.HexColor("#edf5f8")
ANNEXES = {
    '1': "Annexe 1 – Grille de recueil de l'information préoccupante",
    '2': "Annexe 2 – Cellule d'évaluation : plan d'action et propositions",
    '3': "Annexe 3 – Rapport d'évaluation : intervention des services de police",
    '3bis': "Annexe 3 bis – Courrier de transmission au procureur (services de police)",
    '4': "Annexe 4 – Classement sans suite",
    '5': "Annexe 5 – Rapport d'évaluation : accompagnement social non contractualisé",
}
# Annexe liée à chaque proposition de la cellule
PROPOSITION_POUR_ANNEXE = {'3': 'POLICE', '3bis': 'POLICE', '4': 'CLASSEMENT', '5': 'ACCOMPAGNEMENT'}


def _texte(valeur):
    if valeur in (None, "", []):
        return "—"
    if isinstance(valeur, (list, tuple)):
        valeur = ", ".join(str(v) for v in valeur)
    return str(valeur).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")


def _styles():
    base = getSampleStyleSheet()
    return {
        "titre": ParagraphStyle("TitreAV", parent=base["Title"], fontName="Helvetica-Bold", fontSize=13,
                                leading=16, textColor=BLEU, alignment=TA_CENTER, spaceAfter=4),
        "entete": ParagraphStyle("EnteteAV", parent=base["BodyText"], fontSize=9, leading=12),
        "cellule": ParagraphStyle("CelluleAV", parent=base["BodyText"], fontSize=9, leading=11.5),
        "section": ParagraphStyle("SectionAV", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=10,
                                  leading=13, textColor=BLEU, spaceBefore=6, spaceAfter=3),
        "texte": ParagraphStyle("TexteAV", parent=base["BodyText"], fontSize=10, leading=14, spaceAfter=6),
    }


def _p(valeur, style):
    return Paragraph(_texte(valeur), style)


def _tableau(lignes, largeurs):
    table = Table([[_p(a, _styles()["cellule"]), _p(b, _styles()["cellule"])] for a, b in lignes],
                  colWidths=largeurs, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BLEU), ("BACKGROUND", (0, 0), (0, -1), GRIS),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _entete(situation, st):
    mds = situation.mds
    return [
        _p("Direction Générale Adjointe de la Solidarité", st["entete"]),
        _p(f"Maison départementale de la solidarité : {mds.nom if mds else '—'}", st["entete"]),
        _p(f"Date : {timezone.localdate():%d/%m/%Y}", st["entete"]), Spacer(1, 6),
    ]


def _signatures(st):
    return [
        Spacer(1, 10),
        _p("Date, signature et qualité du travailleur social :", st["cellule"]), Spacer(1, 18),
        _p("Validation technique de l'adjoint Cohésion sociale ou du responsable de MDS de proximité :", st["cellule"]),
        Spacer(1, 18),
        _p("Décision administrative du directeur de la MDS (date, signature) :", st["cellule"]), Spacer(1, 18),
    ]


def _identite(situation):
    return [
        ("Nom", situation.personne_nom), ("Prénom", situation.personne_prenom),
        ("Date de naissance", situation.personne_naissance), ("Adresse", situation.personne_adresse),
        ("N° de dossier", situation.numero),
    ]


def _recueil(situation, st):
    origine = situation.get_origine_display()
    if situation.institution:
        origine += f" : {situation.institution}"
    elements = [dict(ELEMENTS).get(e, e) for e in situation.elements]
    return [
        _p("1 – Origine de l'information", st["section"]),
        _tableau([
            ("Date de réception", situation.date_reception), ("Mode de recueil", situation.get_mode_recueil_display()),
            ("Origine", origine),
            ("Signalant", f"{situation.signalant_nom or 'anonyme'} – {situation.signalant_qualite}"),
            ("Coordonnées du signalant", situation.signalant_contact),
            ("Connaît la personne", "oui" if situation.signalant_connait_personne else "non"),
        ], [48 * mm, 130 * mm]),
        _p("2 – Intervenants auprès de la personne", st["section"]),
        _p(situation.intervenants_actuels or "—", st["cellule"]),
        _p("3 – Éléments de l'information préoccupante", st["section"]),
        _p(f"Éléments : {_texte(elements)} · Danger immédiat : {'oui' if situation.danger_immediat else 'non'}", st["cellule"]),
        _p("4 – Nature de l'information : les faits (mot pour mot)", st["section"]),
        _p(situation.faits, st["texte"]),
        _p(f"Événement déclencheur : {situation.evenement_declencheur or '—'}", st["cellule"]),
        _p(f"Depuis quand, répétition : {situation.depuis_quand or '—'}", st["cellule"]),
        _p(f"Comportement, santé : {situation.sante or '—'}", st["cellule"]),
        _p(f"Conditions de vie : {situation.conditions_vie or '—'}", st["cellule"]),
    ]


def _cellule(situation, st):
    cellule = situation.cellule
    return [
        _p("Composition de la cellule", st["section"]), _p(cellule.participants, st["cellule"]),
        _p("Référent(s) de la situation", st["section"]),
        _p(", ".join(u.get_full_name() or u.username for u in cellule.referents.all()) or "—", st["cellule"]),
        _p("Rencontre et investigations", st["section"]),
        _tableau([
            ("Date de la cellule", cellule.date_cellule), ("Rapport attendu",
             f"{cellule.get_urgence_display()} – avant le {situation.date_limite_rapport:%d/%m/%Y}"
             if situation.date_limite_rapport else cellule.get_urgence_display()),
            ("Modalités de la rencontre", f"{cellule.get_modalites_display()} {cellule.modalites_precision}".strip()),
        ], [48 * mm, 130 * mm]),
        _p(cellule.investigations, st["cellule"]),
        _p("Plan d'action et calendrier", st["section"]), _p(cellule.plan_action, st["cellule"]),
        _p("Propositions", st["section"]),
        Paragraph("<br/>".join(
            ("[X] " if code in cellule.propositions else "[ ] ") + _texte(label)
            for code, label in PROPOSITIONS), st["cellule"]),
        _p("Argumentation", st["section"]), _p(cellule.argumentation, st["cellule"]),
    ]


def _titre(numero, st):
    return [_p(ANNEXES[numero], st["titre"]), Spacer(1, 6)]


def rendre_annexe(situation, numero, destination):
    """Génère l'annexe demandée dans destination (fichier ou buffer)."""
    if numero not in ANNEXES:
        raise ValueError(f"Annexe inconnue : {numero}")
    st = _styles()
    doc = SimpleDocTemplate(destination, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm, title=ANNEXES[numero])
    histoire = _titre(numero, st) + _entete(situation, st)
    if numero == '1':
        histoire += _recueil(situation, st) + _signatures(st)
    elif numero == '2':
        histoire += _cellule(situation, st) + _signatures(st)
    elif numero == '3':
        histoire += [_p("Concernant", st["section"]), _tableau(_identite(situation), [48 * mm, 130 * mm]),
                     _p("1 – Motifs et origine de l'information préoccupante", st["section"]),
                     _p(situation.faits, st["texte"]),
                     _p("2 – Limites de l'intervention des services départementaux", st["section"]),
                     _p("Refus de la personne de recevoir le travailleur social, ou impossibilité de contact "
                        "et d'évaluation après avoir mobilisé tous les moyens disponibles.", st["cellule"]),
                     _p("Argumentation et conclusion : demande d'intervention des services de police.",
                        st["section"]),
                     _p(situation.cellule.argumentation, st["cellule"])] + _signatures(st)
    elif numero == '3bis':
        histoire += [
            _p("Monsieur le Procureur de la République, près le tribunal judiciaire,", st["texte"]),
            _p("Objet : signalement en vue de l'intervention des services de police.", st["texte"]),
            _p("J'ai l'honneur de vous faire parvenir un rapport d'évaluation concernant le signalement de "
               f"{situation.libelle_personne}, domicilié(e) : {situation.personne_adresse or '—'}.", st["texte"]),
            _p("Je vous serais obligé de bien vouloir me faire connaître la suite que vous réserverez à ma demande.",
               st["texte"]),
            Spacer(1, 14),
            _p("Pour la Présidente du Conseil départemental, et par délégation,", st["cellule"]),
            _p("Le directeur de la Maison départementale de la solidarité", st["cellule"]),
            Spacer(1, 18), _p("Signature :", st["cellule"]),
        ]
    elif numero == '4':
        histoire += [_p("Personne concernée", st["section"]), _tableau(_identite(situation), [48 * mm, 130 * mm]),
                     _p("Informations recueillies", st["section"]), _p(situation.faits, st["cellule"]),
                     _p("Évaluation : dates de la cellule et principaux éléments", st["section"]),
                     _p(f"Cellule du {situation.cellule.date_cellule:%d/%m/%Y}", st["cellule"]),
                     _p(situation.cellule.investigations, st["cellule"]),
                     _p("Motifs du classement sans suite (en quoi l'évaluation ne retrouve pas les éléments "
                        "recueillis à l'origine)", st["section"]),
                     _p(situation.cellule.argumentation, st["cellule"])] + _signatures(st)
    elif numero == '5':
        histoire += [_p("Renseignements administratifs", st["section"]),
                     _tableau(_identite(situation), [48 * mm, 130 * mm]),
                     _p("Motifs et origine de l'information préoccupante", st["section"]),
                     _p(situation.faits, st["cellule"]),
                     _p("Analyse du service social départemental : faits et hypothèses", st["section"]),
                     _p(situation.cellule.investigations, st["cellule"]),
                     _p("Propositions de mise en place d'un plan d'action", st["section"]),
                     _p(situation.cellule.plan_action, st["cellule"]),
                     _p("Durée de l'accompagnement et date de réévaluation", st["section"]),
                     _p("À compléter selon le plan d'action validé.", st["cellule"])] + _signatures(st)
    doc.build(histoire)


def annexe_disponible(situation, numero):
    """Une annexe liée à une proposition n'est proposée que si la cellule la retient."""
    if numero == '1':
        return True
    cellule = getattr(situation, 'cellule', None)
    if not cellule:
        return False
    if numero == '2':
        return True
    return PROPOSITION_POUR_ANNEXE.get(numero) in cellule.propositions
