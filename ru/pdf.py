# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# ru/pdf.py
"""Génération des supports PDF du circuit Relation Usager (TERU)."""
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from core.signature import libelle_signature

BLEU = colors.HexColor("#1476a8")
VERT = colors.HexColor("#77965c")


def _texte(valeur):
    return (str(valeur) if valeur not in (None, "") else "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")


def _styles():
    base = getSampleStyleSheet()
    return {
        "titre": ParagraphStyle("TitreRU", parent=base["Title"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=BLEU, alignment=TA_CENTER, spaceAfter=4),
        "sous_titre": ParagraphStyle("SousTitreRU", parent=base["Normal"], fontName="Helvetica-BoldOblique", fontSize=12, leading=15, textColor=VERT, alignment=TA_CENTER),
        "cellule": ParagraphStyle("CelluleRU", parent=base["BodyText"], fontSize=8.5, leading=11, spaceAfter=1),
        "petit": ParagraphStyle("PetitRU", parent=base["BodyText"], fontSize=7.5, leading=9),
        "texte": ParagraphStyle("TexteRU", parent=base["BodyText"], fontSize=10, leading=15, spaceAfter=6),
    }


def _pdf_doc(destination, title):
    return SimpleDocTemplate(destination, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=14*mm, bottomMargin=14*mm, title=title)


def _p(text, style):
    return Paragraph(_texte(text), style)


def _table(rows, widths, background_first=True):
    rules = [
        ("GRID", (0, 0), (-1, -1), 0.6, BLEU),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if background_first:
        rules.append(("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf5f8")))
    table = Table(rows, colWidths=widths, hAlign="LEFT")
    table.setStyle(TableStyle(rules))
    return table


def rendre_formulaire(demande, destination):
    """TERU, aligné sur le gabarit DOTM de rapport social fourni par le Département."""
    styles = _styles()
    cellule, petit = styles["cellule"], styles["petit"]
    doc = _pdf_doc(destination, f"TERU {demande.reference}")
    p = lambda value, style=cellule: _p(value, style)
    largeur = A4[0] - 32*mm
    date_transmission = demande.date_notification_mds.strftime("%d/%m/%Y") if demande.date_notification_mds else "—"
    date_cloture = demande.date_cloture_souhaitee.strftime("%d/%m/%Y") if demande.date_cloture_souhaitee else (demande.date_echeance.strftime("%d/%m/%Y") if demande.date_echeance else "—")
    rdv1 = " — ".join(x for x in [demande.date_premier_rendez_vous.strftime("%d/%m/%Y") if demande.date_premier_rendez_vous else "—", demande.heure_premier_rendez_vous.strftime("%H:%M") if demande.heure_premier_rendez_vous else "heure à préciser"])
    rdv2 = " — ".join(x for x in [demande.date_second_rendez_vous.strftime("%d/%m/%Y") if demande.date_second_rendez_vous else "—", demande.heure_second_rendez_vous.strftime("%H:%M") if demande.heure_second_rendez_vous else "heure à préciser"])
    contenu = [
        _table([[p("DÉPARTEMENT DES BOUCHES-DU-RHÔNE", petit), p("Numéro de dossier : " + demande.reference, petit)],
                [p("DGAS / DITAS / DAAS<br/>Service action sociale", petit), p("N° SAP : " + (demande.reference_sap or "—"), petit)],
                [p("", petit), p("Date de transmission : " + date_transmission, petit)]], [largeur*0.53, largeur*0.47]),
        Spacer(1, 7*mm),
        Paragraph("MAISON DÉPARTEMENTALE DE LA SOLIDARITÉ DE : " + _texte(demande.mds.nom if demande.mds else "—"), styles["titre"]),
        Spacer(1, 3*mm),
        Paragraph("TERU — Traitement électronique des relations aux usagers", styles["sous_titre"]),
        Spacer(1, 4*mm),
        _table([
            [p("Nom et prénom"), p(f"{demande.nom_usager} {demande.prenom_usager}")],
            [p("Adresse"), p(demande.adresse_usager)],
            [p("Transmission"), p(demande.get_circuit_display())],
            [p("Motif"), p(demande.objet)],
            [p("Priorité"), p(demande.get_priorite_display())],
            [p("À clôturer avant le"), p(date_cloture)],
            [p("Si réponse directe par le SAS, le préciser"), p(getattr(getattr(demande, "fiche_retour_sas", None), "synthese_reponse", ""))],
            [p("Situation familiale"), p(demande.situation_familiale)],
            [p("Nombre d'enfants à charge"), p(demande.nombre_enfants)],
            [p("Revenu principal"), p(demande.revenu_principal)],
            [p("Âge du demandeur"), p(demande.age_usager)],
        ], [largeur*0.34, largeur*0.66]),
        Spacer(1, 4*mm),
        _table([
            [p("Date / heure du 1er RDV"), p(rdv1), p("Ne s'est pas présenté"), p("[X]" if demande.absence_premier_rendez_vous else "[ ]")],
            [p("Date / heure du 2e RDV"), p(rdv2), p("Ne s'est pas présenté"), p("[X]" if demande.absence_second_rendez_vous else "[ ]")],
        ], [largeur*0.28, largeur*0.25, largeur*0.29, largeur*0.18]),
        Spacer(1, 4*mm),
        Paragraph("ÉVALUATION SOCIALE SYNTHÉTIQUE", styles["sous_titre"]),
        Spacer(1, 2*mm),
        _table([
            [p("Demande de l'usager"), p(demande.resume_demande)],
            [p("Éléments déclaratifs"), p(demande.elements_declaratifs)],
            [p("Problématique repérée / plan préconisé"), p(demande.problematique_plan or demande.evaluation_sociale)],
            [p("Contacts et démarches réalisés"), p(demande.modalites_contact)],
            [p("Situation actualisée"), p(demande.situation_actualisee)],
            [p("Plan d'aide / échéances"), p(demande.plan_aide)],
            [p("Réorientation proposée"), p(demande.propositions_reorientation)],
        ], [largeur*0.31, largeur*0.69]),
        Spacer(1, 2*mm),
        p("Aide AMASE / SAA / autre : " + (demande.aide_financiere_type or "—")
          + " | Décision : " + (demande.decision_aide_financiere or "—")
          + " | Montant : " + (str(demande.montant_aide_financiere) + " €" if demande.montant_aide_financiere is not None else "—")
          + " | Date : " + (demande.date_aide_financiere.strftime("%d/%m/%Y") if demande.date_aide_financiere else "—"), petit),
        p("Motif du rejet, le cas échéant : " + (demande.motif_rejet_aide or "—"), petit),
        Spacer(1, 4*mm),
        _table([
            [p("Nom du travailleur social"), p(demande.agent_assigne.get_full_name() if demande.agent_assigne else "")],
            [p("Visa du cadre (initiales / signature nominative)"), p((demande.initiales_signature_cadre + " · " if demande.initiales_signature_cadre else "") + (libelle_signature(demande.validee_par) if demande.validee_par else ""))],
            [p("Date et heure de validation"), p(timezone.localtime(demande.date_validation_mds).strftime("%d/%m/%Y à %H:%M") if demande.date_validation_mds else "")],
        ], [largeur*0.46, largeur*0.54]),
        Spacer(1, 3*mm),
        p("PDF généré par CID pour transmission numérique et consultation. Vérifier les informations communicables avant l'envoi. Le secret professionnel s'applique au présent document.", petit),
    ]
    doc.build(contenu)


def rendre_fiche_retour_sas(fiche, destination):
    styles = _styles()
    demande = fiche.demande
    largeur = A4[0] - 32*mm
    doc = _pdf_doc(destination, f"Fiche retour SAS {demande.reference}")
    transmis = timezone.localtime(fiche.date_transmission).strftime("%d/%m/%Y à %H:%M") if fiche.date_transmission else "Brouillon – transmission non enregistrée"
    contenu = [
        Paragraph("FICHE DE RETOUR SAS", styles["titre"]),
        Paragraph("Relation Usager — réponse et suite donnée", styles["sous_titre"]),
        Spacer(1, 6*mm),
        _table([
            [_p("N° dossier", styles["cellule"]), _p(demande.reference, styles["cellule"])],
            [_p("N° SAP", styles["cellule"]), _p(demande.reference_sap, styles["cellule"])],
            [_p("Usager", styles["cellule"]), _p(f"{demande.nom_usager} {demande.prenom_usager}", styles["cellule"])],
            [_p("Service émetteur", styles["cellule"]), _p(demande.emetteur, styles["cellule"])],
            [_p("MDS", styles["cellule"]), _p(demande.mds.nom if demande.mds else "—", styles["cellule"])],
            [_p("Type de réponse / suite", styles["cellule"]), _p(fiche.get_type_reponse_display(), styles["cellule"])],
            [_p("Service réorienté", styles["cellule"]), _p(fiche.service_reoriente, styles["cellule"])],
        ], [largeur*0.33, largeur*0.67]),
        Spacer(1, 5*mm),
        Paragraph("Réponse à l'usager et au service émetteur", styles["sous_titre"]),
        Spacer(1, 2*mm),
        _table([[_p(fiche.synthese_reponse, styles["texte"])]], [largeur], background_first=False),
        Spacer(1, 4*mm),
        Paragraph("Suite donnée / observations", styles["sous_titre"]),
        Spacer(1, 2*mm),
        _table([[_p(fiche.suite_donnee, styles["texte"])]], [largeur], background_first=False),
        Spacer(1, 8*mm),
        _table([
            [_p("Transmission enregistrée dans CID", styles["cellule"]), _p(transmis, styles["cellule"])],
            [_p("Agent SAS", styles["cellule"]), _p(fiche.transmis_par.get_full_name() if fiche.transmis_par else "—", styles["cellule"])],
        ], [largeur*0.4, largeur*0.6]),
        Spacer(1, 5*mm),
        _p("Ce document est généré par CID pour la transmission numérique ou l'impression si nécessaire. Le système n'envoie pas automatiquement de courrier ou courriel externe.", styles["petit"]),
    ]
    doc.build(contenu)


def rendre_courrier_rdv(demande, rang, destination):
    styles = _styles()
    largeur = A4[0] - 32*mm
    date_rdv = demande.date_premier_rendez_vous if rang == 1 else demande.date_second_rendez_vous
    heure_rdv = demande.heure_premier_rendez_vous if rang == 1 else demande.heure_second_rendez_vous
    numero = "premier" if rang == 1 else "second"
    doc = _pdf_doc(destination, f"Courrier RDV {rang} {demande.reference}")
    now = timezone.localtime()
    rendez_vous = date_rdv.strftime("%d/%m/%Y")
    if heure_rdv:
        rendez_vous += f" à {heure_rdv.strftime('%H:%M')}"
    else:
        rendez_vous += " (heure à confirmer par la MDS)"
    mds = demande.mds
    lieu = f"{mds.nom}\n{mds.adresse}\n{mds.code_postal} {mds.ville}" if mds else "Maison départementale de la solidarité"
    contenu = [
        Paragraph("DÉPARTEMENT DES BOUCHES-DU-RHÔNE", styles["titre"]),
        Paragraph("DGAS / DITAS / DAAS · Service action sociale", styles["petit"]),
        Spacer(1, 8*mm),
        _p(f"Dossier : {demande.reference}", styles["cellule"]),
        _p(f"{demande.prenom_usager} {demande.nom_usager}", styles["texte"]),
        _p(demande.adresse_usager, styles["texte"]),
        Spacer(1, 5*mm),
        _p(f"{mds.ville if mds else ''}, le {now:%d/%m/%Y}", styles["texte"]),
        Spacer(1, 5*mm),
        Paragraph(f"Objet : proposition de {numero} rendez-vous", styles["sous_titre"]),
        Spacer(1, 5*mm),
        _p("Bonjour,", styles["texte"]),
        _p(f"Afin d'étudier votre demande (référence {demande.reference}), nous vous proposons un rendez-vous à la date suivante :", styles["texte"]),
        Spacer(1, 2*mm),
        _table([
            [_p("Date et heure", styles["cellule"]), _p(rendez_vous, styles["cellule"])],
            [_p("Lieu", styles["cellule"]), _p(lieu, styles["cellule"])],
        ], [largeur*0.28, largeur*0.72]),
        Spacer(1, 6*mm),
        _p("Merci de vous présenter avec les documents utiles à l'examen de votre situation. Si vous ne pouvez pas être présent(e), veuillez contacter votre MDS afin de convenir d'une nouvelle date.", styles["texte"]),
        _p("Veuillez recevoir nos salutations respectueuses.", styles["texte"]),
        Spacer(1, 8*mm),
        _p("Votre travailleur social", styles["cellule"]),
        _p(demande.agent_assigne.get_full_name() if demande.agent_assigne else "Service action sociale", styles["texte"]),
        Spacer(1, 10*mm),
        _p("Courrier PDF généré par CID. La génération ne signifie pas que le courrier a été expédié; le service doit vérifier les informations puis enregistrer son envoi selon ses pratiques.", styles["petit"]),
    ]
    doc.build(contenu)
