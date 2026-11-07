# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/fsl_pdf.py
"""Dossier FSL accès à imprimer : formulaires officiels du gestionnaire remplis par CID (pagination d'origine),
ou, à défaut, une trame générique CID avec les mêmes rubriques."""
import io
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from logement.models import FormulaireOfficiel as F

from . import placements_fsl
from .fsl import (COLONNES, EQUIPEMENTS, GARANTIES, LOGEMENT_ANTERIEUR, LOGEMENT_NOUVEAU, PIECES, PROPOSITION,
                  RESSOURCES_FSL, ROLES, SITUATIONS_FAMILIALES, d, montant, taux_effort, totaux_ressources)
from .pdf_officiel import remplir


def documents_du_dossier(demande):
    """[(code, raison)] dans l'ordre du dossier, selon la demande."""
    dn = demande.donnees or {}
    pret = bool(d(demande.proposition_pret))
    garantie = bool(dn.get('garantie'))
    out = [(F.FORMULAIRE_ACCES, "toujours"), (F.AVIS_MOTIVE, "toujours")]
    if demande.pieces_manquantes and demande.date_validation_cadre:
        out.append((F.ARGUMENTAIRE, "pièces manquantes"))
    if pret:
        out.append((F.CONTRAT_PRET, "prêt proposé"))
    if pret or garantie:
        out.append((F.PRELEVEMENT, "remboursement par prélèvement"))
    if garantie:
        out.append((F.CONTRAT_GARANTIE, "garantie de paiement demandée"))
    out.append((F.CONVENTION_ACCES, "toujours"))
    if dn.get('bailleur_type') == 'PRIVE':
        out.append((F.IDENTIFICATION_LOGEMENT, "bailleur privé"))
    if d((dn.get('logement_nouveau') or {}).get('al_previsionnel')):
        out.append((F.VERSEMENT_DIRECT_AL, "aide au logement versée au bailleur"))
    out.append((F.LISTE_PIECES, "toujours"))
    return out


def dossier(demande):
    """(pdf, rapport) ; rapport = [(libellé, 'officiel' | 'trame CID' | 'à joindre vierge', détail)]."""
    from pypdf import PdfReader, PdfWriter
    sortie = PdfWriter()
    rapport = []
    generique_fait = False
    for code, raison in documents_du_dossier(demande):
        libelle = dict(F.CODES)[code]
        modele = F.pour(code, demande.gestionnaire)
        if modele:
            pdf, r = remplir(bytes(modele.contenu), placements_fsl.placements(code),
                             placements_fsl.valeurs(demande, code), modele.reglages)
            manque = [k for k, v in r.items() if v not in ('ok', 'vide')]
            rapport.append((libelle, 'officiel', f"{len(manque)} champ(s) non placé(s)" if manque else ""))
        elif code in (F.FORMULAIRE_ACCES, F.AVIS_MOTIVE, F.ARGUMENTAIRE, F.LISTE_PIECES):
            if generique_fait:
                rapport.append((libelle, 'trame CID', "dans la trame"))
                continue
            pdf = trame_generique(demande)
            generique_fait = True
            rapport.append((libelle, 'trame CID', "formulaire, avis, pièces et note du cadre réunis"))
        else:
            rapport.append((libelle, 'à joindre vierge', f"{raison} : formulaire du gestionnaire non déposé dans CID"))
            continue
        for page in PdfReader(io.BytesIO(pdf)).pages:
            sortie.add_page(page)
    out = io.BytesIO()
    sortie.write(out)
    return out.getvalue(), rapport


# ---------------------------------------------------------------------------------------------------------------
# Trame générique (sans formulaire officiel déposé)

def _t(v):
    return escape(str(v or "")).replace("\n", "<br/>")


def _grille(lignes, largeurs, entete=True, fusion=()):
    t = Table(lignes, colWidths=largeurs, repeatRows=1 if entete else 0)
    style = [('SPAN', a, b) for a, b in fusion] + [('GRID', (0, 0), (-1, -1), 0.4, colors.grey), ('FONTSIZE', (0, 0), (-1, -1), 8),
             ('VALIGN', (0, 0), (-1, -1), 'TOP')]
    if entete:
        style += [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]
    t.setStyle(TableStyle(style))
    return t


def trame_generique(demande):
    from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles
    st = get_ditas_styles()
    dn = demande.donnees or {}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=3.5 * cm,
                            bottomMargin=2 * cm, title="Demande FSL accès", author="CID")
    P = lambda texte, style="Normal": Paragraph(texte, st[style])  # noqa: E731
    COCHE = lambda ok: "[X]" if ok else "[  ]"  # noqa: E731
    el = [P("DEMANDE D'AIDE À L'ACCÈS AU LOGEMENT – FONDS DE SOLIDARITÉ POUR LE LOGEMENT", "TitreOfficiel"),
          P(f"<b>Gestionnaire :</b> {_t(demande.gestionnaire or 'à préciser')} &nbsp; "
            f"<i>(trame générique CID : le formulaire officiel du gestionnaire n'est pas déposé)</i>"), Spacer(1, 6)]
    el.append(_grille([
        [P(f"{COCHE(dn.get('bailleur_type') == 'SOCIAL')} Bailleur social &nbsp; {COCHE(dn.get('bailleur_type') == 'PRIVE')} Bailleur privé"),
         P(f"<b>N° allocataire CAF :</b> {_t(dn.get('num_caf'))} &nbsp; <b>Autres :</b> {_t(dn.get('autres_numero'))}")],
        [P(f"<b>Adresse objet de la demande :</b> {_t(dn.get('adresse_objet'))} {_t(dn.get('cp_commune'))}"),
         P(f"<b>Nouveau bailleur :</b> {_t(dn.get('nouveau_bailleur'))}<br/>{_t(dn.get('contact_bailleur'))}")],
    ], [9 * cm, 9 * cm], entete=False))
    el += [Spacer(1, 6), P("Situation familiale", "SectionHeader"),
           P(" &nbsp; ".join(f"{COCHE(dn.get('situation_familiale') == c)} {l}" for c, l in SITUATIONS_FAMILIALES))]
    roles = dict(ROLES)
    lignes = [["", "Nom", "Prénom", "Naissance", "Nationalité", "Situation actuelle"]]
    for p in dn.get('composition') or []:
        lignes.append([roles.get(p.get('role'), ''), p.get('nom', ''), p.get('prenom', ''), p.get('date_naissance', ''),
                       p.get('nationalite', ''), P(_t(p.get('situation', '') + (f" ({p['lien']})" if p.get('lien') else '')))])
    el.append(_grille(lignes, [2.6 * cm, 3.2 * cm, 3 * cm, 2.2 * cm, 2.4 * cm, 4.6 * cm]))
    el += [Spacer(1, 6), P("Ressources mensuelles du foyer (mois précédant la signature)", "SectionHeader")]
    res = dn.get('ressources') or {}
    prec = dn.get('ressources_precisions') or {}
    lignes = [["Ressources"] + [l for _, l in COLONNES]]
    for code, libelle, _ in RESSOURCES_FSL:
        if code.startswith('autres') and code not in res:
            continue
        lignes.append([P(_t(libelle + (f" : {prec[code]}" if prec.get(code) else '')))]
                      + [montant((res.get(code) or {}).get(col)) for col, _ in COLONNES])
    par_col, total = totaux_ressources(res)
    lignes.append(["TOTAL"] + [montant(par_col[c]) for c, _ in COLONNES])
    el.append(_grille(lignes, [6 * cm, 4 * cm, 4 * cm, 4 * cm]))
    el.append(P(f"<b>Total des ressources :</b> {montant(total)} € &nbsp; <b>Quotient familial :</b> "
                f"{_t(dn.get('quotient_familial'))} &nbsp; <b>Taux d'effort (indicatif) :</b> {taux_effort(dn)} %"))
    ant, nv = dn.get('logement_anterieur') or {}, dn.get('logement_nouveau') or {}
    lignes = [["Logement antérieur au relogement", "", "Logement objet de la demande", ""]]
    a = [(l, ant.get(c)) for c, l in LOGEMENT_ANTERIEUR] + [("Caution restituée", ant.get('caution_restituee'))]
    n = [(l, nv.get(c)) for c, l in LOGEMENT_NOUVEAU] + [("Chauffage collectif", nv.get('chauffage_collectif'))]
    for i in range(max(len(a), len(n))):
        la = a[i] if i < len(a) else ("", "")
        ln = n[i] if i < len(n) else ("", "")
        lignes.append([P(_t(la[0])), P(_t(la[1])), P(_t(ln[0])), P(_t(ln[1]))])
    el += [Spacer(1, 6), _grille(lignes, [4.5 * cm, 4.5 * cm, 4.5 * cm, 4.5 * cm], fusion=(((0, 0), (1, 0)), ((2, 0), (3, 0))))]
    prop = dn.get('proposition') or {}
    el += [Spacer(1, 6), P("Proposition du travailleur social", "SectionHeader"),
           P(f"<b>Garantie de paiement :</b> {dict(GARANTIES).get(dn.get('garantie', ''), '')}")]
    lignes = [["Aide aux frais d'installation", "Proposition TS", "Réservé FSL"]]
    for c, l in PROPOSITION:
        lignes.append([l, montant(prop.get(c)), ""])
    lignes.append(["Total proposé", montant(sum((d(v) for v in prop.values()), d(0))), ""])
    el.append(_grille(lignes, [9 * cm, 4.5 * cm, 4.5 * cm]))
    eq = [l for c, l in EQUIPEMENTS if c in (dn.get('equipements') or [])]
    if eq:
        el.append(P(f"<b>Équipements :</b> {_t(', '.join(eq))}"))
    ts = dn.get('ts') or {}
    el += [Spacer(1, 6), P("Coordonnées du travailleur social", "SectionHeader"),
           P(f"{_t(ts.get('prenom'))} {_t(ts.get('nom'))} – {_t(ts.get('qualite'))}<br/>"
             f"Tél. {_t(ts.get('telephone'))} {_t(ts.get('portable'))} – {_t(ts.get('email'))}<br/>{_t(ts.get('organisme'))}"),
           Spacer(1, 6),
           _grille([["Date et signature du demandeur", "Date et signature du travailleur social", "Cachet de la structure"],
                    ["\n\n\n", "", ""]], [6 * cm, 6 * cm, 6 * cm])]
    # avis motivé
    el += [Spacer(1, 10), P("Avis motivé et proposition du travailleur social", "SectionHeader"),
           P(" &nbsp; ".join(f"{COCHE(demande.avis == c)} {l}" for c, l in demande.AVIS)),
           P(_t(demande.avis_motive)),
           P(f"<b>Proposition :</b> prêt {montant(demande.proposition_pret) or '–'} € ; subvention "
             f"{montant(demande.proposition_subvention) or '–'} €")]
    # pièces
    etats = demande.pieces or {}
    lignes = [["Pièce", "État"]]
    for c, l, _ in PIECES:
        if c in etats:
            lignes.append([P(_t(l)), {'FOURNIE': "Fournie", 'MANQUANTE': "À fournir", 'SANS_OBJET': "Sans objet"}[etats[c]]])
    el += [Spacer(1, 6), P("Pièces du dossier", "SectionHeader"), _grille(lignes, [14 * cm, 4 * cm])]
    if demande.note_cadre:
        from mds.fonctions import nom_et_fonction
        el += [Spacer(1, 6), P("Note explicative du cadre (pièces manquantes)", "SectionHeader"), P(_t(demande.note_cadre)),
               P(f"Le {demande.date_validation_cadre:%d/%m/%Y} – {_t(nom_et_fonction(demande.cadre, demande.mds))}"
                 if demande.date_validation_cadre and demande.cadre else "")]
    el.append(P(f"<i>Édité par CID le {timezone.localdate():%d/%m/%Y}.</i>"))
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    return buf.getvalue()
