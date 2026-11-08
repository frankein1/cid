# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/expulsion_pdf.py
"""Fiche de liaison « Prévention de l'expulsion locative » (page 1) et fiche CAF « Prévention de l'expulsion
domiciliaire » (page 2), reprises rubrique par rubrique. Les coordonnées du Service Logement viennent de
l'administration (paramètre SERVICE_LOGEMENT_COORDONNEES), jamais du code."""
import io
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from logement.models.m_expulsion import CHAMPS_CAF, DECISION_CASES, DUREES_DELAI


def _t(v):
    return escape(str(v if v not in (None, '') else "")).replace("\n", "<br/>")


def _d(v):
    return v.strftime('%d/%m/%Y') if v else ""


def _e(v):
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",") if v is not None else ""


def _case(v):
    return "<b>[X]</b>" if v else "[&nbsp;&nbsp;]"


def coordonnees_sl():
    from core.models import Configuration
    try:
        return Configuration.get('SERVICE_LOGEMENT_COORDONNEES', '') or ''
    except Exception:
        return ''


def fiche(d):
    from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles
    st = get_ditas_styles()
    P = lambda t, s="Normal": Paragraph(t, st[s])  # noqa: E731
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=3.5 * cm,
                            bottomMargin=2 * cm, title=f"Prévention des expulsions {d.numero}", author="CID")
    grille = [('GRID', (0, 0), (-1, -1), 0.4, colors.grey), ('FONTSIZE', (0, 0), (-1, -1), 8),
              ('VALIGN', (0, 0), (-1, -1), 'TOP')]

    def tableau(lignes, largeurs, entete=False):
        t = Table([[P(c) if isinstance(c, str) else c for c in l] for l in lignes], colWidths=largeurs)
        t.setStyle(TableStyle(grille + ([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb'))] if entete else [])))
        return t

    # ---------------------------------------------------------------- page 1 : fiche de liaison
    el = [P("PRÉVENTION DE L'EXPULSION LOCATIVE<br/>ASSIGNATIONS AUX FINS DE RÉSILIATION DE BAIL<br/>"
            "FICHE DE LIAISON CD 13 – CAF 13", "TitreOfficiel"),
          P(f"<b>Dossier n° :</b> {_t(d.numero)} – <b>Date :</b> {_d(d.date_reception)} – "
            f"<b>MDS :</b> {_t(d.mds or 'à affecter')}")]
    if coordonnees_sl():
        el.append(P(f"<i>{_t(coordonnees_sl())}</i>"))
    el += [Spacer(1, 6), tableau([
        [f"<b>Nom :</b> {_t(d.nom.upper())}", f"<b>Prénom :</b> {_t(d.prenom)}"],
        [f"<b>Coloc. :</b> {_t(d.colocataire)}", ""],
        [f"<b>Adresse :</b> {_t(d.adresse_complete)}",
         f"<b>Date de l'audience :</b> {_d(d.date_audience)} {_t(d.heure_audience)}<br/>{_t(d.tribunal)}"],
    ], [10 * cm, 8 * cm]), Spacer(1, 4), tableau([
        [f"<b>Propriétaire</b> ({_t(d.get_type_bailleur_display())})<br/>{_t(d.proprietaire)}"]], [18 * cm]),
        Spacer(1, 4), tableau([
            ["<b>Logement</b>", f"Date de signature du bail : {_d(d.date_signature_bail)}", ""],
            [f"Montant mensuel total du loyer : {_e(d.loyer_total)}", f"Loyer : {_e(d.loyer)}", f"Charges : {_e(d.charges)}"],
            [f"<b>Montant de la dette réclamée par le bailleur :</b> {_e(d.dette)}", f"à la date du {_d(d.dette_au)}", ""],
        ], [8 * cm, 5.5 * cm, 4.5 * cm]), Spacer(1, 4)]
    obs = d.observation_caf
    el.append(tableau([
        [f"<b>Observations</b>", f"<b>Allocataire :</b> {_t(d.numero_allocataire)}"],
        [f"{_case(obs == 'FICHE_CAF')} Fiche CAF<br/>{_case(obs == 'SERVICE_SOCIAL_CAF')} Service social CAF<br/>"
         f"{_case(obs == 'NON_IDENTIFIE')} Non identifié CAF – retour le {_d(d.retour_le)}",
         f"{_case(d.association)} Association &nbsp;&nbsp; {_case(d.ccas)} CCAS"],
    ], [10 * cm, 8 * cm]))
    dec = d.decision or {}
    lignes = [[f"<b>Décision du tribunal du</b> {_d(d.date_decision)}"]]
    for cle, lib in DECISION_CASES:
        texte = f"{_case(dec.get(cle))} {lib}"
        if cle == 'provisions' and dec.get('provisions_montant'):
            texte += f" – montant : {_t(dec['provisions_montant'])} €"
        if cle == 'accord_delai':
            texte += " – " + " ".join(f"{_case(dec.get('duree_delai') == c)} {l}" for c, l in DUREES_DELAI)
            if dec.get('duree_autre'):
                texte += f" ({_t(dec['duree_autre'])})"
        lignes.append([texte])
    el += [Spacer(1, 4), tableau(lignes, [18 * cm])]
    if d.observations:
        el += [Spacer(1, 4), P(f"<b>Observations du Service Logement :</b> {_t(d.observations)}")]

    # ---------------------------------------------------------------- page 2 : fiche CAF
    caf = d.caf or {}
    if caf or d.numero_allocataire:
        el += [PageBreak(), P("PRÉVENTION DE L'EXPULSION DOMICILIAIRE<br/>(fiche CAF)", "TitreOfficiel"),
               P(f"<b>Date d'audience :</b> {_d(d.date_audience)} – <b>N° allocataire :</b> {_t(d.numero_allocataire)}")]
        rubriques = {}
        for cle, lib, rub in CHAMPS_CAF:
            rubriques.setdefault(rub, []).append([lib, _t(caf.get(cle))])
        for i, (rub, lignes) in enumerate(rubriques.items(), 1):
            el += [Spacer(1, 4), P(f"{i} – {rub.upper()}", "SectionHeader"), tableau(lignes, [7 * cm, 11 * cm])]
    el += [Spacer(1, 8), P(f"<i>Édité par CID le {timezone.localdate():%d/%m/%Y}.</i>")]
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    return buf.getvalue()
