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
    '6': "Annexe 6 – Rapport d'évaluation : demande de MASP niveau I ou II",
    '7': "Annexe 7 – Rapport d'évaluation : intervention auprès des services de psychiatrie",
    '7bis': "Annexe 7 bis – Courrier de transmission au médecin chef du service de psychiatrie",
    '8': "Annexe 8 – Rapport de signalement au médecin inspecteur de l'ARS",
    '8bis': "Annexe 8 bis – Courrier de transmission au médecin inspecteur de l'ARS",
    '9': "Annexe 9 – Rapport de signalement en vue d'une protection juridique",
    '9bis': "Annexe 9 bis – Courrier de transmission au procureur (protection juridique)",
}
# Annexe liée à chaque proposition de la cellule
PROPOSITION_POUR_ANNEXE = {
    '3': 'POLICE', '3bis': 'POLICE', '4': 'CLASSEMENT', '5': 'ACCOMPAGNEMENT', '6': 'MASP',
    '7': 'PSYCHIATRIE', '7bis': 'PSYCHIATRIE', '8': 'ARS', '8bis': 'ARS',
    '9': 'PROTECTION_JURIDIQUE', '9bis': 'PROTECTION_JURIDIQUE',
}
COURRIER_TGI = [
    "Monsieur le Procureur de la République, près le tribunal judiciaire,",
    "Objet : signalement en vue d'une mesure de protection juridique d'un majeur.",
]


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


def _masp_contenu(situation, st):
    masp = getattr(situation, 'masp', None)
    niveau = masp.get_niveau_display() if masp else "à préciser"
    return [
        _p("Direction de la cohésion sociale – Service de la protection des majeurs", st["entete"]),
        _p("Renseignements administratifs", st["section"]),
        _tableau(_identite(situation) + [("Mesure demandée", niveau)], [48 * mm, 130 * mm]),
        _p("Situation vis-à-vis de l'emploi, conditions de logement", st["section"]),
        _p(situation.personne_adresse or "—", st["cellule"]),
        _p("Données budgétaires au moment de la demande (à compléter)", st["section"]),
        _tableau([("Ressources du mois", " "), ("Charges du mois (loyer, énergie, assurances, impôts…)", " "),
                  ("Total général", " ")], [80 * mm, 98 * mm]),
        _p("Référent social", st["section"]),
        _p(f"{masp.referent_nom} – {masp.referent_qualite}" if masp else "—", st["cellule"]),
        _p("Analyse et proposition", st["section"]),
        _p(situation.cellule.argumentation or situation.cellule.plan_action, st["cellule"]),
    ]


def _signalement_contenu(situation, numero, st):
    """Rapports 7, 8 et 9 : mêmes rubriques, orientées vers le destinataire."""
    cellule = situation.cellule
    destinataire = {'7': "Médecin chef du service de psychiatrie",
                    '8': "Médecin inspecteur de l'ARS",
                    '9': "Procureur de la République : demande de protection juridique"}[numero]
    lignes = [("Destinataire", destinataire), ("Nom", situation.personne_nom),
              ("Prénom", situation.personne_prenom), ("Date de naissance", situation.personne_naissance),
              ("Adresse", situation.personne_adresse)]
    if numero == '9':
        lignes += [("Parquet", situation.get_tribunal_display()), ("Mesure demandée", situation.get_mesure_protection_display())]
    contenu = [_p(destinataire, st["section"]), _tableau(lignes, [48 * mm, 130 * mm]),
               _p("Origine et nature de l'information préoccupante", st["section"]),
               _p(situation.faits, st["cellule"]),
               _p("Contexte et parcours de la personne", st["section"]),
               _p(situation.evenement_declencheur or "—", st["cellule"]),
               _p("Intervention des services sociaux, médicaux et médico-sociaux", st["section"]),
               _p(cellule.investigations or "—", st["cellule"]),
               _p("Analyse et conclusion", st["section"]),
               _p(cellule.argumentation or "—", st["cellule"])]
    if numero == '7':
        contenu += [_p("Proposition d'intervention sollicitée auprès des services de psychiatrie", st["section"]),
                    _p(cellule.plan_action, st["cellule"])]
    elif numero == '8':
        contenu += [_p("Intervention sollicitée auprès de l'Agence régionale de santé", st["section"]),
                    _p(cellule.plan_action, st["cellule"])]
    else:
        contenu += [_p("Mesure proposée (tutelle, curatelle, sauvegarde de justice)", st["section"]),
                    _p(situation.get_mesure_protection_display(), st["cellule"]),
                    _p("Avis de l'intéressé(e) : à compléter", st["cellule"]),
                    _p("Pièces jointes : copie d'un justificatif d'état civil ; fiche de renseignements du "
                       "parquet concerné ; certificat médical circonstancié (expert choisi sur la liste du procureur).",
                       st["cellule"])]
    return contenu


def _courrier_contenu(situation, numero, st):
    if numero == '7bis':
        objet = f"Objet : signalement de la situation de {situation.libelle_personne}."
        corps = ["Je tiens à vous alerter sur la situation de l'intéressé(e).",
                 "Je vous serais obligé de bien vouloir me faire connaître la suite à donner à ce signalement."]
        destinataire = ["Monsieur le Médecin chef", "du service de psychiatrie"]
    elif numero == '8bis':
        objet = f"Objet : signalement de la situation de {situation.libelle_personne}."
        corps = ["Je tiens à vous alerter sur la situation de l'intéressé(e) suite :",
                 "– à un refus de soins de sa part ;",
                 "– à l'impossibilité de mettre en place une prise en charge médicale.",
                 "Je vous serais obligé de bien vouloir me faire connaître la suite à donner à ce signalement."]
        destinataire = ["Monsieur le Médecin inspecteur de l'Agence régionale de santé",
                        "Immeuble M'Square, 132 bd de Paris, 13003 Marseille"]
    else:
        objet = "Objet : signalement en vue d'une mesure de protection juridique d'un majeur."
        corps = ["J'ai l'honneur de vous faire parvenir : le rapport d'évaluation sociale, la fiche de "
                 "renseignements dûment remplie, la copie d'un justificatif d'état civil, le certificat médical "
                 "circonstancié.",
                 "Je vous serais obligé de bien vouloir me faire connaître votre décision."]
        destinataire = ["Monsieur le Procureur de la République", "près le tribunal judiciaire"]
    contenu = [Paragraph("<br/>".join(_texte(d) for d in destinataire), st["texte"]),
               _p(objet, st["texte"]), _p(f"Concernant : {situation.libelle_personne}, domicilié(e) : "
                                          f"{situation.personne_adresse or '—'}", st["texte"])]
    contenu += [_p(c, st["texte"]) for c in corps]
    contenu += [Spacer(1, 12), _p("Pour la Présidente du Conseil départemental, et par délégation,", st["cellule"]),
                _p("Le directeur de la Maison départementale de la solidarité", st["cellule"]),
                Spacer(1, 16), _p("Signature :", st["cellule"])]
    return contenu


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
    elif numero == '6':
        histoire += _masp_contenu(situation, st) + _signatures(st)
    elif numero in ('7', '8', '9'):
        histoire += _signalement_contenu(situation, numero, st) + _signatures(st)
    elif numero in ('7bis', '8bis', '9bis'):
        histoire += _courrier_contenu(situation, numero, st)
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
