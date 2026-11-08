# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/expulsion_documents.py
"""Documents de la MDS pour la prévention des expulsions, tous produits en PDF par CID :
  - convocations au diagnostic (1re, 2e et dernière) : textes modifiables en administration (Modèles de courriers) ;
  - courrier et questionnaire au bailleur ;
  - diagnostic social et financier (Cerfa 16227*01, voir dsf.py) ou bordereau de carence.
Le questionnaire bailleur et le bordereau de carence sont des documents locaux : déposés en administration
(Formulaires officiels, codes EXP_QUEST_BAILLEUR et EXP_CARENCE), sinon CID imprime une trame aux mêmes rubriques."""
import io
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from logement.models import ConvocationExpulsion, DiagnosticExpulsion
from logement.models import FormulaireOfficiel as F


def _t(v):
    return escape(str(v or "")).replace("\n", "<br/>")


def _d(x, heure=False):
    if not x:
        return ""
    if hasattr(x, 'hour'):
        x = timezone.localtime(x)
        return x.strftime("%d/%m/%Y à %H:%M" if heure else "%d/%m/%Y")
    return x.strftime("%d/%m/%Y")


def _doc(buf, titre):
    return SimpleDocTemplate(buf, pagesize=A4, topMargin=3.5 * cm, bottomMargin=2 * cm, leftMargin=2 * cm,
                             rightMargin=2 * cm, title=titre, author="CID")


def _styles():
    from AidFi.services.afase_pdf import get_ditas_styles
    return get_ditas_styles()


def _construire(buf, elements):
    from AidFi.services.afase_pdf import draw_page_template
    _doc(buf, "CID").build(elements, onFirstPage=draw_page_template, onLaterPages=draw_page_template)


def _bloc_mds(mds, st):
    if not mds:
        return []
    return [Paragraph(f"<b>{_t(mds.nom)}</b><br/>{_t(mds.adresse)}<br/>{_t(mds.code_postal)} {_t(mds.ville)}"
                      + (f"<br/>Tél. {_t(mds.telephone)}" if mds.telephone else "")
                      + (f"<br/>{_t(mds.email)}" if mds.email else ""), st["Normal"]), Spacer(1, 0.5 * cm)]


def _adresse(lignes, st):
    return [Table([["", Paragraph("<br/>".join(_t(l) for l in lignes if l), st["Normal"])]],
                  colWidths=[9 * cm, 8 * cm]), Spacer(1, 0.8 * cm)]


def _valeurs_communes(dossier):
    from beneficiaire.transfert import responsable_mds
    from mds.fonctions import fonction_de
    mds = dossier.mds
    resp = responsable_mds(mds)
    b = dossier.beneficiaire
    civ = getattr(b, 'civilite', '') if b else ''
    return {
        "civilite_appel": "Monsieur" if civ in ('M', 'M.', 'MR') else "Madame" if civ in ('MME', 'Mme') else "Madame, Monsieur",
        "locataire": f"{(b.prenom if b else dossier.prenom)} {(b.nom if b else dossier.nom).upper()}".strip(),
        "adresse_locataire": dossier.adresse_complete,
        "date_audience": _d(dossier.date_audience), "tribunal": dossier.tribunal,
        "mds": f"{mds.nom}, {mds.adresse}, {mds.code_postal} {mds.ville}" if mds else "la Maison départementale de la solidarité",
        "telephone_mds": (mds.telephone if mds else "") or "la MDS",
        "signataire": (resp.get_full_name() or resp.username) if resp else "",
        "signataire_fonction": (fonction_de(resp, mds) or "") if resp else "",
    }, {"si_tribunal": bool(dossier.tribunal), "si_audience": bool(dossier.date_audience)}


def _courrier(dossier, code, valeurs, conditions, destinataire, date_courrier, st, elements):
    from core.courriers import modele_texte, rendu
    m = modele_texte(code)
    elements += _bloc_mds(dossier.mds, st) + _adresse(destinataire, st)
    elements += [Paragraph(f"{_t(dossier.mds.ville if dossier.mds else '')}, le {_d(date_courrier)}", st["Normal"]),
                 Spacer(1, 0.4 * cm),
                 Paragraph(f"<b>Objet :</b> {rendu.ligne(m['objet'], valeurs, conditions)}", st["Normal"]),
                 Spacer(1, 0.4 * cm)]
    for p in rendu.paragraphes(m["corps"], valeurs, conditions):
        elements += [Paragraph(p, st["Normal"]), Spacer(1, 0.25 * cm)]
    if m.get("signature"):
        elements += [Spacer(1, 0.6 * cm), Table([["", Paragraph(rendu.ligne(m["signature"], valeurs, conditions)
                                                                .replace("\n", "<br/>"), st["Normal"])]],
                                                colWidths=[9 * cm, 8 * cm])]


# ------------------------------------------------------------------------------------------------- convocations
def convocation_pdf(conv: ConvocationExpulsion):
    dossier = conv.dossier
    valeurs, conditions = _valeurs_communes(dossier)
    mds = dossier.mds
    valeurs.update({"date_rdv": _d(conv.date_rdv, heure=True),
                    "lieu": conv.lieu or (f"la {mds.nom}, {mds.adresse}, {mds.code_postal} {mds.ville}" if mds else "la MDS"),
                    "agent": (conv.agent.get_full_name() if conv.agent else "un travailleur social de la MDS")})
    code = "EXP_CONVOCATION_DSF"
    if conv.passage_id:
        com = conv.passage.commission
        code = "EXP_CONVOCATION_COMMISSION" if conv.type_convocation == ConvocationExpulsion.COM_1 \
            else "EXP_RELANCE_COMMISSION"
        valeurs.update({"commission": com.get_type_commission_display().lower(),
                        "date_commission": _d(com.date)})
        prec = conv.passage.convocations.exclude(pk=conv.pk).order_by('-date_rdv').first()
        valeurs["date_precedente"] = _d(prec.date_rdv, heure=True) if prec else "précédemment"
    elif conv.type_convocation == ConvocationExpulsion.DSF_2:
        code = "EXP_CONVOCATION_DSF_2"
        prec = dossier.convocations.filter(type_convocation=ConvocationExpulsion.DSF_1).order_by('-date_rdv').first()
        valeurs["date_precedente"] = _d(prec.date_rdv, heure=True) if prec else "précédemment"
    b = dossier.beneficiaire
    adresse = [valeurs["locataire"], (b.adresse if b else dossier.adresse),
               f"{(b.code_postal if b else dossier.code_postal)} {(b.ville if b else dossier.ville)}"]
    buf, st, el = io.BytesIO(), _styles(), []
    _courrier(dossier, code, valeurs, conditions, adresse, conv.date_courrier, st, el)
    _construire(buf, el)
    return buf.getvalue()


# ------------------------------------------------------------------------------------------------- bailleur
def _questionnaire_trame(dossier, date_retour, st):
    mds = dossier.mds
    def tab(lignes, largeurs):
        t = Table([[Paragraph(c, st["Normal"]) for c in l] for l in lignes], colWidths=largeurs)
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('FONTSIZE', (0, 0), (-1, -1), 8)]))
        return t
    c = "[&nbsp;&nbsp;]"
    el = [Paragraph("QUESTIONNAIRE À REMPLIR PAR LE BAILLEUR POUR L'ÉTABLISSEMENT DU DIAGNOSTIC SOCIAL ET FINANCIER",
                    st["TitreOfficiel"]),
          Paragraph("Vous avez assigné votre locataire pour impayés de loyers devant le juge des contentieux de la "
                    "protection. Le diagnostic social et financier informe le magistrat sur la situation de votre "
                    "locataire et permet d'apprécier l'impact de la dette locative sur votre propre situation. "
                    f"Merci de compléter les deux volets et de les retourner <b>avant le {_d(date_retour)}</b> à : "
                    f"<b>{_t(mds.nom if mds else '')}</b> – {_t(mds.adresse if mds else '')} {_t(mds.code_postal if mds else '')} "
                    f"{_t(mds.ville if mds else '')}" + (f" – {_t(mds.email)}" if mds and mds.email else "") + ".",
                    st["Normal"]), Spacer(1, 6),
          Paragraph("INFORMATIONS CONCERNANT LE LOCATAIRE", st["SectionHeader"]),
          tab([[f"<b>Nom, prénom du ou des locataires :</b> {_t(dossier.nom_complet)}"
                + (f", {_t(dossier.colocataire)}" if dossier.colocataire else ""),
                f"<b>Montant du loyer :</b> {_t(dossier.loyer or dossier.loyer_total or '……')} €<br/><b>Charges :</b> {_t(dossier.charges or '……')} €"],
               [f"<b>Adresse :</b> {_t(dossier.adresse_complete)}",
                f"<b>Aide au logement :</b> ……… € (CAF / MSA)<br/>Versée au bailleur : {c} oui {c} non"],
               ["<b>Téléphone, mail du locataire :</b><br/><br/>",
                f"<b>N° allocataire :</b> {_t(dossier.numero_allocataire)}"],
               [f"<b>Type de logement :</b> {c} T1 {c} T2 {c} T3 {c} T4 {c} T5 ou +<br/>"
                f"Logement sur-occupé {c} sous-occupé {c}", ""],
               ["<b>État de la dette</b><br/>Montant actualisé : ……… €<br/>Arrêté au : ………<br/>Origine de la dette :<br/><br/>",
                f"Impayé signalé à la CAF ou à la MSA : {c} oui {c} non<br/>"
                f"Assurance contre les impayés de loyer : {c} oui {c} non"]], [9 * cm, 8 * cm]),
          Spacer(1, 8), Paragraph("INFORMATIONS CONCERNANT LE BAILLEUR", st["SectionHeader"]),
          tab([["<b>Bailleur personne physique</b><br/>Nom, prénom :<br/><br/>En cas d'indivision, représentant légal :"
                "<br/><br/>Gestionnaire du bien (le cas échéant) :<br/><br/>",
                f"<b>Bailleur personne morale</b><br/>Société et représentant légal :<br/><br/>Nature : SCI familiale "
                f"{c} SCI non familiale {c} Autre : ………<br/>Gestionnaire du bien (le cas échéant) :<br/><br/>"],
               ["<b>Adresse :</b><br/><br/>", "<b>Téléphone, mail :</b><br/><br/>"]], [9 * cm, 8 * cm]),
          PageBreak(),
          Paragraph("SITUATION DU BAILLEUR (personne physique, SCI familiale, indivision)", st["SectionHeader"]),
          tab([[f"<b>Situation professionnelle :</b> en activité {c} sans emploi {c} (depuis le ………) "
                f"retraité {c} étudiant {c} autre : ………"],
               [f"<b>Situation familiale :</b> marié {c} célibataire {c} vie maritale {c} – nombre d'enfants : ……"],
               [f"<b>Situation patrimoniale :</b> propriétaire occupant de votre résidence principale {c} – "
                f"locataire de votre résidence principale {c} (loyer et charges : ……… € ; aide au logement : ……… €) – "
                f"autre hébergement : ……… – multipropriétaire de biens locatifs {c} : autres impayés ? {c} oui {c} non"],
               [f"<b>Difficultés de paiement :</b> votre loyer {c} – remboursement de vos prêts {c} – charges de "
                f"copropriété {c} – autres : ………<br/>Aide sociale sollicitée : {c} oui {c} non, laquelle : ………<br/>"
                f"Dossier de surendettement déposé : {c} oui {c} non"]], [17 * cm]),
          Spacer(1, 8)]
    for q in ("Quels ont été les impacts de l'impayé de loyer sur votre situation ?",
              "Avez-vous pu trouver une entente amiable avec votre locataire ? Si oui, les engagements pris ont-ils "
              "été tenus ?",
              "Vos observations sur la situation d'impayé de votre locataire :"):
        el += [Paragraph(f"<b>{q}</b>", st["Normal"]), Spacer(1, 2.6 * cm)]
    el += [Paragraph("Questionnaire établi le ……………… &nbsp;&nbsp;&nbsp;&nbsp; Signature :", st["Normal"])]
    return el


def placements_questionnaire():
    """Formulaire local déposé en administration : seules les rubriques connues du dossier sont remplies."""
    return [{'cle': 'date_retour', 'ancre': 'retourner avant le', 'dx': 4},
            {'cle': 'locataire', 'ancre': 'Nom, Prénom des locataires', 'mode': 'dessous', 'dy': 2},
            {'cle': 'adresse', 'ancre': 'Adresse :', 'occ': 0, 'dx': 4, 'taille': 8},
            {'cle': 'loyer', 'ancre': 'Montant du loyer', 'occ': 0, 'dx': 4},
            {'cle': 'charges', 'ancre': 'Charges :', 'occ': 0, 'dx': 4},
            {'cle': 'numero_caf', 'ancre': 'n° allocataire', 'dx': 4}]


def questionnaire_pdf(dossier, date_retour):
    from pypdf import PdfReader, PdfWriter
    from .pdf_officiel import remplir
    valeurs, conditions = _valeurs_communes(dossier)
    valeurs["date_retour"] = _d(date_retour)
    st = _styles()
    destinataire = [l for l in (dossier.proprietaire or "Le bailleur").split("\n")]
    buf, el = io.BytesIO(), []
    _courrier(dossier, "EXP_QUESTIONNAIRE_BAILLEUR", valeurs, conditions, destinataire, timezone.localdate(), st, el)
    modele = F.objects.filter(code=F.EXP_QUESTIONNAIRE, actif=True).exclude(contenu=b'').first()
    if not modele:
        el += [PageBreak()] + _questionnaire_trame(dossier, date_retour, st)
        _construire(buf, el)
        return buf.getvalue()
    _construire(buf, el)
    rempli, _ = remplir(bytes(modele.contenu), placements_questionnaire(), {
        'date_retour': _d(date_retour), 'locataire': dossier.nom_complet, 'adresse': dossier.adresse_complete,
        'loyer': str(dossier.loyer or dossier.loyer_total or ''), 'charges': str(dossier.charges or ''),
        'numero_caf': dossier.numero_allocataire}, modele.reglages)
    sortie = PdfWriter()
    for morceau in (buf.getvalue(), rempli):
        for page in PdfReader(io.BytesIO(morceau)).pages:
            sortie.add_page(page)
    out = io.BytesIO()
    sortie.write(out)
    return out.getvalue()


# ------------------------------------------------------------------------------------------------- DSF, carence
def valeurs_carence(diag):
    from .fsl import coordonnees_ts
    d = diag.dossier
    absences = [_d(c.date_rdv) for c in d.convocations.filter(statut=ConvocationExpulsion.ABSENT,
                                                              type_convocation__in=ConvocationExpulsion.TYPES_DSF).order_by('date_rdv')]
    ts = coordonnees_ts(diag.redacteur, d.mds)
    from .placements_fsl import visa
    texte, image = visa(diag)
    v = {'audience': _d(d.date_audience), 'nom': d.nom.upper(), 'prenom': d.prenom,
         'adresse': d.adresse_complete, 'exploc': d.numero_exploc, 'caf': d.numero_allocataire,
         'convocations': ", ".join(absences), 'ts_nom': (ts['nom'] or '').upper(), 'ts_prenom': ts['prenom'],
         'organisme': ts['organisme'], 'date': _d(timezone.localdate()), 'visa': texte}
    v.update({k: x for k, x in (diag.donnees or {}).items() if k in v and x})
    if image:
        v['visa_image'] = image
    return v


def placements_carence():
    x = 175
    return [{'cle': 'audience', 'ancre': 'Audience du', 'dx': 4},
            {'cle': 'nom', 'ancre': 'NOM', 'occ': 0, 'x_abs': x}, {'cle': 'prenom', 'ancre': 'Prénom', 'occ': 0, 'x_abs': x},
            {'cle': 'adresse', 'ancre': 'Adresse', 'occ': 0, 'x_abs': x, 'taille': 8},
            {'cle': 'exploc', 'ancre': 'N° de dossier EXPLOC', 'x_abs': x},
            {'cle': 'caf', 'ancre': 'N° allocataire CAF ou MSA', 'x_abs': x},
            {'cle': 'convocations', 'ancre': 'Dates des convocations non honorées', 'mode': 'dessous', 'dy': 3},
            {'cle': 'ts_nom', 'ancre': 'NOM', 'occ': 1, 'x_abs': x}, {'cle': 'ts_prenom', 'ancre': 'Prénom', 'occ': 1, 'x_abs': x},
            {'cle': 'organisme', 'ancre': "Organisme d", 'x_abs': x, 'taille': 8},
            {'cle': 'date', 'ancre': 'Date', 'occ': 0, 'top_min': 600, 'x_abs': x},
            {'cle': 'visa', 'ancre': 'Signature et cachet', 'x_abs': x},
            {'cle': 'visa_image', 'ancre': 'Signature et cachet', 'x_abs': x, 'mode': 'dessous', 'dy': 6}]


def _carence_trame(diag):
    v = valeurs_carence(diag)
    st = _styles()
    lignes = [["<b>Expulsion locative – assignation – audience du</b>", v['audience']],
              ["<b>Ménage – NOM</b>", v['nom']], ["Prénom", v['prenom']], ["Adresse", v['adresse']],
              ["N° de dossier EXPLOC", v['exploc']], ["N° allocataire CAF ou MSA", v['caf']],
              ["Dates des convocations non honorées", v['convocations']],
              ["<b>Travailleur social – NOM</b>", v['ts_nom']], ["Prénom", v['ts_prenom']],
              ["Organisme d'appartenance", v['organisme']], ["Date", v['date']], ["Signature et cachet", v['visa']]]
    t = Table([[Paragraph(a, st["Normal"]), Paragraph(_t(b), st["Normal"])] for a, b in lignes],
              colWidths=[7 * cm, 10 * cm])
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    el = [Paragraph("BORDEREAU DE CARENCE", st["TitreOfficiel"]),
          Paragraph("À remplir par l'organisme chargé du diagnostic social et financier, au stade de l'assignation, "
                    "uniquement si toutes ces conditions sont réunies : absence du locataire à l'entretien ; absence "
                    "d'observations transmises ensuite ; absence d'informations de la CCAPEX locale ; absence "
                    "d'informations du bailleur malgré une tentative de contact.", st["Normal"]),
          Spacer(1, 8), t, Spacer(1, 8),
          Paragraph("Le service n'est pas en mesure de communiquer de diagnostic social et financier.", st["Normal"])]
    buf = io.BytesIO()
    _construire(buf, el)
    return buf.getvalue()


def document(diag: DiagnosticExpulsion):
    """PDF à transmettre : Cerfa DSF rempli, ou bordereau de carence (formulaire local, sinon trame CID)."""
    from .placements_fsl import visa
    if diag.type_document == DiagnosticExpulsion.DSF:
        from .dsf import remplir_cerfa
        return remplir_cerfa(diag.donnees, visa(diag))
    modele = F.objects.filter(code=F.EXP_CARENCE, actif=True).exclude(contenu=b'').first()
    if not modele:
        return _carence_trame(diag)
    from .pdf_officiel import remplir
    pdf, _ = remplir(bytes(modele.contenu), placements_carence(), valeurs_carence(diag), modele.reglages)
    return pdf
