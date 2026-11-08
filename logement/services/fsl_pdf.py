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


TRAME = {F.FORMULAIRE_ACCES, F.AVIS_MOTIVE, F.ARGUMENTAIRE, F.LISTE_PIECES, F.FORMULAIRE_EAU, F.FORMULAIRE_ENERGIE,
         F.AVIS_FLUIDES, F.ARGUMENTAIRE_FLUIDES, F.FORMULAIRE_MAINTIEN, F.ARGUMENTAIRE_MAINTIEN, F.LISTE_PIECES_MAINTIEN}


def documents_du_dossier(demande):
    """[(code, raison)] dans l'ordre du dossier, selon la demande."""
    dn = demande.donnees or {}
    if demande.est_fluides:
        out = [(F.FORMULAIRE_EAU if demande.type_aide == 'EAU' else F.FORMULAIRE_ENERGIE, "toujours")]
        if not demande.instruction_administrative:
            out.append((F.AVIS_FLUIDES, "avis du travailleur social"))
        if demande.pieces_manquantes and demande.date_validation_cadre:
            out.append((F.ARGUMENTAIRE_FLUIDES, "pièces manquantes"))
        return out
    pret = bool(d(demande.proposition_pret))
    if demande.type_aide == 'MAINTIEN':
        out = [(F.FORMULAIRE_MAINTIEN, "toujours"), (F.AVIS_MOTIVE, "toujours")]
        if demande.pieces_manquantes and demande.date_validation_cadre:
            out.append((F.ARGUMENTAIRE_MAINTIEN, "pièces manquantes"))
        if pret:
            out += [(F.CONTRAT_PRET, "prêt proposé"), (F.PRELEVEMENT, "remboursement par prélèvement")]
        out.append((F.ENGAGEMENTS, "toujours"))
        if demande.est_concordat:
            out.append((F.CONVENTION_CONCORDAT, "concordat"))
        if dn.get('bailleur_type') == 'PRIVE':
            out.append((F.IDENTIFICATION_LOGEMENT, "bailleur privé"))
        if d((dn.get('logement') or {}).get('al')):
            out.append((F.VERSEMENT_DIRECT_AL, "aide au logement versée au bailleur"))
        out.append((F.LISTE_PIECES_MAINTIEN, "toujours"))
        return out
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
            pdf, r = remplir(bytes(modele.contenu), placements_fsl.placements(code, demande.type_aide),
                             placements_fsl.valeurs(demande, code), modele.reglages)
            manque = [k for k, v in r.items() if v not in ('ok', 'vide')]
            rapport.append((libelle, 'officiel', f"{len(manque)} champ(s) non placé(s)" if manque else ""))
        elif code in TRAME:
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
    titres = {'ACCES': "DEMANDE D'AIDE À L'ACCÈS AU LOGEMENT", 'EAU': "DEMANDE D'AIDE AUX IMPAYÉS D'EAU",
              'ENERGIE': "DEMANDE D'AIDE AUX IMPAYÉS D'ÉLECTRICITÉ, DE GAZ",
              'MAINTIEN': "DEMANDE FSL CONCORDAT" if demande.est_concordat else "DEMANDE FSL MAINTIEN"}
    el = [P(f"{titres[demande.type_aide]} – FONDS DE SOLIDARITÉ POUR LE LOGEMENT", "TitreOfficiel"),
          P(f"<b>Gestionnaire :</b> {_t(demande.gestionnaire or 'à préciser')} &nbsp; "
            f"<i>(trame générique CID : le formulaire officiel du gestionnaire n'est pas déposé)</i>"), Spacer(1, 6)]
    if demande.type_aide == 'MAINTIEN':
        from .fsl import LOGEMENT_MAINTIEN
        lg = dn.get('logement') or {}
        oui_non = lambda cle: f"{COCHE(dn.get(cle) == 'OUI')} oui {COCHE(dn.get(cle) == 'NON')} non"  # noqa: E731
        el.append(_grille([
            [P(f"{COCHE(dn.get('bailleur_type') == 'SOCIAL')} Bailleur social &nbsp; {COCHE(dn.get('bailleur_type') == 'PRIVE')} Bailleur privé"),
             P(f"<b>N° allocataire CAF :</b> {_t(dn.get('num_caf'))} &nbsp; <b>Autres :</b> {_t(dn.get('autres_numero'))}")],
            [P(f"<b>Adresse :</b> {_t(dn.get('adresse'))} {_t(dn.get('cp_commune'))}"),
             P(f"<b>Bailleur :</b> {_t(dn.get('nom_bailleur'))}<br/>{_t(dn.get('contact_bailleur'))}")],
            [P(" &nbsp; ".join(f"<b>{l} :</b> {_t(lg.get(c))}" for c, l in LOGEMENT_MAINTIEN)),
             P(f"<b>Chauffage collectif :</b> {oui_non('chauffage_collectif')}<br/><b>Saisine de la commission de "
               f"surendettement :</b> {oui_non('saisine_surendettement')}<br/><b>Saisine de la CCAPEX :</b> {oui_non('saisine_ccapex')}")],
            [P(f"<b>Dette locative :</b> {montant(dn.get('montant_dette'))} € &nbsp; <b>Reprise du paiement depuis :</b> "
               f"{_t(dn.get('reprise_paiement_depuis'))}"),
             P(f"<b>Concordat – remise de dette du bailleur :</b> {oui_non('remise_dette')} {montant(dn.get('montant_remise'))} €"
               if demande.est_concordat else "FSL maintien : reprise du paiement du résiduel de loyer de 3 mois consécutifs")],
        ], [9 * cm, 9 * cm], entete=False))
    elif demande.est_fluides:
        from .fsl import SITUATIONS_LOGEMENT
        el.append(_grille([
            [P(f"<b>{'Distributeur' if demande.type_aide == 'EAU' else 'Fournisseur d’énergie'} :</b> {_t(dn.get('distributeur'))}"),
             P(f"<b>N° allocataire CAF :</b> {_t(dn.get('num_caf'))} &nbsp; <b>Autres :</b> {_t(dn.get('autres_numero'))}")],
            [P(f"<b>Adresse :</b> {_t(dn.get('adresse'))} {_t(dn.get('cp_commune'))}"),
             P(f"<b>Loyer et charges ou mensualité du prêt :</b> {montant(dn.get('montant_loyer'))} €")],
        ], [9 * cm, 9 * cm], entete=False))
        el.append(P(" &nbsp; ".join(f"{COCHE(dn.get('situation_logement') == c)} {l}" for c, l in SITUATIONS_LOGEMENT)))
    else:
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
                f"{_t(dn.get('quotient_familial'))}"
                + ("" if demande.est_fluides else f" &nbsp; <b>Taux d'effort (indicatif) :</b> {taux_effort(dn)} %")))
    if demande.est_fluides:
        return _fin_fluides(demande, dn, el, P, COCHE, doc)
    if demande.type_aide == 'MAINTIEN':
        return _fin_maintien(demande, dn, el, P, COCHE, doc)
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
    el += _visa_trame(demande, P)
    el.append(P(f"<i>Édité par CID le {timezone.localdate():%d/%m/%Y}.</i>"))
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    return buf.getvalue()


def _fin_fluides(demande, dn, el, P, COCHE, doc):
    from AidFi.services.afase_pdf import draw_page_template
    from .fsl import PIECES_FLUIDES
    el += [Spacer(1, 6), P("Dette", "SectionHeader")]
    if demande.type_aide == 'EAU':
        el.append(P(f"<b>Facture du :</b> {_t(dn.get('date_facture'))} &nbsp; <b>Montant :</b> {montant(dn.get('montant_facture'))} €"))
    else:
        el.append(P(f"<b>Dette d'électricité :</b> {montant(dn.get('dette_electricite')) or '–'} € &nbsp; "
                    f"<b>Dette de gaz :</b> {montant(dn.get('dette_gaz')) or '–'} € &nbsp; "
                    f"<b>Participation du ménage :</b> {COCHE(dn.get('participation') == 'OUI')} oui "
                    f"{COCHE(dn.get('participation') == 'NON')} non"))
        if dn.get('plan_fournisseur'):
            el.append(P(f"<b>Plan de financement du fournisseur :</b> {_t(dn.get('plan_fournisseur'))}"))
    el.append(P(f"<b>Charges exceptionnelles :</b> {_t(dn.get('charges_exceptionnelles'))}<br/>"
                f"<b>Facture incluse dans un dossier de surendettement :</b> {COCHE(dn.get('surendettement') == 'OUI')} oui "
                f"{COCHE(dn.get('surendettement') == 'NON')} non"))
    ts = dn.get('ts') or {}
    el += [Spacer(1, 6), P("Coordonnées de l'agent instructeur", "SectionHeader"),
           P(f"{_t(ts.get('prenom'))} {_t(ts.get('nom'))} – {_t(ts.get('qualite'))}<br/>"
             f"Tél. {_t(ts.get('telephone'))} {_t(ts.get('portable'))} – {_t(ts.get('email'))}<br/>{_t(ts.get('organisme'))}")]
    if demande.instruction_administrative:
        el += [P("<b>Instruite par un agent administratif</b> (facture de moins de 500 €)"),
               P(_t(dn.get('commentaire_administratif')))]
    else:
        el += [Spacer(1, 6), P("Avis motivé du travailleur social", "SectionHeader"),
               P(" &nbsp; ".join(f"{COCHE(demande.avis == c)} {l}" for c, l in demande.AVIS)), P(_t(demande.avis_motive))]
    el += [Spacer(1, 6), P("Je m'engage à régler le solde qui restera à ma charge et mes futures consommations."),
           _grille([["Date et signature du demandeur", "Date et signature de l'agent instructeur", "Cachet de la structure"],
                    ["\n\n\n", "", ""]], [6 * cm, 6 * cm, 6 * cm])]
    etats = demande.pieces or {}
    lignes = [["Pièce", "État"]]
    for c, l, _ in PIECES_FLUIDES:
        if c in etats:
            lignes.append([P(_t(l)), {'FOURNIE': "Fournie", 'MANQUANTE': "À fournir", 'SANS_OBJET': "Sans objet"}[etats[c]]])
    el += [Spacer(1, 6), P("Pièces du dossier", "SectionHeader"), _grille(lignes, [14 * cm, 4 * cm])]
    if demande.note_cadre:
        from mds.fonctions import nom_et_fonction
        el += [Spacer(1, 6), P("Note explicative du cadre (pièces manquantes)", "SectionHeader"), P(_t(demande.note_cadre)),
               P(f"Le {demande.date_validation_cadre:%d/%m/%Y} – {_t(nom_et_fonction(demande.cadre, demande.mds))}"
                 if demande.date_validation_cadre and demande.cadre else "")]
    el += _visa_trame(demande, P)
    el.append(P(f"<i>Édité par CID le {timezone.localdate():%d/%m/%Y}.</i>"))
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    return doc.filename.getvalue()


def _fin_maintien(demande, dn, el, P, COCHE, doc):
    from AidFi.services.afase_pdf import draw_page_template
    from .fsl import PIECES_MAINTIEN
    ts = dn.get('ts') or {}
    el += [Spacer(1, 6), P("Coordonnées du travailleur social", "SectionHeader"),
           P(f"{_t(ts.get('prenom'))} {_t(ts.get('nom'))} – {_t(ts.get('qualite'))}<br/>"
             f"Tél. {_t(ts.get('telephone'))} {_t(ts.get('portable'))} – {_t(ts.get('email'))}<br/>{_t(ts.get('organisme'))}"),
           Spacer(1, 6), P("Avis motivé et proposition du travailleur social", "SectionHeader"),
           P(" &nbsp; ".join(f"{COCHE(demande.avis == c)} {l}" for c, l in demande.AVIS)), P(_t(demande.avis_motive)),
           P(f"<b>Proposition :</b> prêt {montant(demande.proposition_pret) or '–'} € ; subvention "
             f"{montant(demande.proposition_subvention) or '–'} €"),
           Spacer(1, 6),
           _grille([["Date et signature du demandeur", "Date, signature et cachet du bailleur", "Date et signature du travailleur social"],
                    ["\n\n\n", "", ""]], [6 * cm, 6 * cm, 6 * cm])]
    etats = demande.pieces or {}
    lignes = [["Pièce", "État"]]
    for c, l, _ in PIECES_MAINTIEN:
        if c in etats:
            lignes.append([P(_t(l)), {'FOURNIE': "Fournie", 'MANQUANTE': "À fournir", 'SANS_OBJET': "Sans objet"}[etats[c]]])
    el += [Spacer(1, 6), P("Pièces du dossier", "SectionHeader"), _grille(lignes, [14 * cm, 4 * cm])]
    if demande.note_cadre:
        from mds.fonctions import nom_et_fonction
        el += [Spacer(1, 6), P("Note explicative du cadre (pièces manquantes)", "SectionHeader"), P(_t(demande.note_cadre)),
               P(f"Le {demande.date_validation_cadre:%d/%m/%Y} – {_t(nom_et_fonction(demande.cadre, demande.mds))}"
                 if demande.date_validation_cadre and demande.cadre else "")]
    el += _visa_trame(demande, P)
    el.append(P(f"<i>Édité par CID le {timezone.localdate():%d/%m/%Y}.</i>"))
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    return doc.filename.getvalue()


def _visa_trame(demande, P):
    from reportlab.platypus import Image
    texte, image = placements_fsl.visa(demande)
    if not texte:
        return []
    from mds.fonctions import nom_et_fonction
    out = [Spacer(1, 6), P(f"<b>{_t(texte)}</b> – {_t(nom_et_fonction(demande.cadre, demande.mds))}")]
    if image:
        try:
            out.append(Image(io.BytesIO(image['image']), width=3.2 * cm, height=1.1 * cm, kind='proportional'))
        except Exception:
            pass
    return out
