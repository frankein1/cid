# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/services/afase_documents.py
"""
Documents d'une AFASE produits par CID :
  - le formulaire de demande, sur le modèle de l'imprimé de la direction enfance-famille (cadres A à D,
    budget mensuel du ménage, justificatifs, signatures du demandeur, du travailleur social et du cadre) ;
  - le courrier de notification de la décision à l'usager (motivé en fait et en droit, voies de recours).
"""
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles

COCHE, VIDE = "[X]", "[  ]"


def _nom(u):
    return (u.get_full_name() or u.username) if u else ""


def _d(date):
    if not date:
        return ""
    if hasattr(date, 'hour'):
        date = timezone.localtime(date)
    return date.strftime("%d/%m/%Y")


def _e(m):
    try:
        return _fr(m) if m not in (None, "") and float(m) else ""
    except (TypeError, ValueError):
        return ""


def _fr(m):
    """Montant à la française : 1 234,50 €."""
    return f"{float(m):,.2f} €".replace(",", " ").replace(".", ",")


def _txt(v):
    return escape(v or "").replace("\n", "<br/>")


def _p(texte, st, style="Normal"):
    return Paragraph(texte, st[style])


def _grille(lignes, largeurs, entete=True, gras_derniere=False):
    t = Table(lignes, colWidths=largeurs, repeatRows=1 if entete else 0)
    style = [('GRID', (0, 0), (-1, -1), 0.4, colors.grey), ('FONTSIZE', (0, 0), (-1, -1), 8),
             ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 2),
             ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]
    if entete:
        style += [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]
    if gras_derniere:
        style += [('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6'))]
    t.setStyle(TableStyle(style))
    return t


def _section(titre, st):
    return Paragraph(titre, st["SectionHeader"])


# =============================================================================
# FORMULAIRE DE DEMANDE (annexe 1)
# =============================================================================

def formulaire_pdf(demande):
    from AidFi.models.m_generique import PIECES_EQUIVALENTES, PIECES_REQUISES_AFASE
    from AidFi.services import budget_afase
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=3.5 * cm,
                            bottomMargin=2 * cm, title=f"Demande AFASE {demande.pk}", author="CID")
    st = get_ditas_styles()
    b = demande.beneficiaire
    dem = demande.demandeur or b
    ev = getattr(demande, 'evaluation_afase', None)
    budget = getattr(demande, 'budget', None)
    decision = getattr(demande, 'decision', None)
    ts = demande.cree_par
    el = [Paragraph("DEMANDE D'ALLOCATION FINANCIÈRE DE L'AIDE SOCIALE À L'ENFANCE", st["TitreOfficiel"])]

    el.append(_grille([
        [_p(f"<b>Organisme instructeur :</b> {escape(str(demande.mds or ''))}", st),
         _p(f"<b>Nom du travailleur social :</b> {escape(_nom(ts))}", st)],
        [_p(f"{COCHE if demande.premiere_demande else VIDE} 1<super>re</super> demande &nbsp; "
            f"{VIDE if demande.premiere_demande else COCHE} Renouvellement", st),
         _p(f"<b>N° dossier GENESIS :</b> {escape(demande.numero_genesis or b.numero_genesis or '')}", st)],
    ], [9 * cm, 9 * cm], entete=False))

    # A – enfants
    el.append(_section("A – ENFANT(S) MINEUR(S) OU JEUNE(S) MAJEUR(S) DE MOINS DE 21 ANS", st))
    lignes = [["Nom", "Prénom", "Né(e) le", "Sexe", "Situation (scolarité, formation, emploi…)", "Concerné"]]
    for e in demande.enfants.all():
        lignes.append([e.nom, e.prenom, ("Enfant à naître " if e.a_naitre else "") + _d(e.date_naissance), e.sexe,
                       _p(_txt(e.situation), st), COCHE if e.concerne else VIDE])
    if len(lignes) == 1:
        lignes.append(["", "", "", "", "", VIDE])
    el.append(_grille(lignes, [3 * cm, 3 * cm, 2.6 * cm, 1.1 * cm, 6.3 * cm, 2 * cm]))

    # B – demandeur
    el.append(_section("B – DEMANDEUR", st))
    caf = {True: "Oui", False: "Non"}.get(demande.allocataire_caf, "")
    el.append(_grille([
        [_p(f"{COCHE if dem.civilite == 'MME' else VIDE} Madame &nbsp; {COCHE if dem.civilite == 'M.' else VIDE} Monsieur", st),
         _p(f"<b>Lien :</b> {escape(demande.get_lien_demandeur_display() or '')}", st)],
        [_p(f"<b>Nom d'usage :</b> {escape(dem.nom.upper())}", st), _p(f"<b>Prénom :</b> {escape(dem.prenom)}", st)],
        [_p(f"<b>Nom de naissance :</b> {escape(dem.nom_naissance or '')}", st),
         _p(f"<b>Date de naissance :</b> {_d(dem.date_naissance)}", st)],
        [_p(f"<b>Situation familiale :</b> {escape(dem.get_marital_status_display() or '') if dem.marital_status else ''}", st),
         _p(f"<b>Allocataire CAF :</b> {caf}", st)],
        [_p(f"<b>Adresse :</b> {_txt(dem.adresse)}", st), _p(f"<b>Code postal, commune :</b> {escape(dem.code_postal)} {escape(dem.ville)}", st)],
        [_p(f"<b>Situation professionnelle :</b> {escape(demande.situation_pro_demandeur)}", st),
         _p(f"<b>Âge et situation professionnelle du conjoint :</b> {escape(demande.situation_pro_conjoint)}", st)],
    ], [9 * cm, 9 * cm], entete=False))

    # C – coordonnées bancaires
    el.append(_section("C – COORDONNÉES BANCAIRES", st))
    el.append(_p("RIB domicilié en France, au nom du destinataire de l'aide, joint au dossier "
                 f"(original) : {COCHE if demande.pieces_justificatives.filter(type_piece='RIB').exists() else VIDE}", st))

    # D – cadre réservé à la décision
    el.append(_section("D – CADRE RÉSERVÉ À LA DÉCISION", st))
    el.append(_p(f"<b>Montant sollicité :</b> {_e(demande.montant_sollicite)} par mois pendant {demande.duree_demande} mois", st))
    if decision:
        total = (decision.montant_accorde or 0) * (decision.duree_accordee or 1)
        accord = decision.type_decision == 'ACCORD'
        ligne = [_e(decision.montant_accorde) if accord else "", str(decision.duree_accordee or "") if accord else "",
                 _e(total) if accord else "", demande.code_demande or "",
                 decision.code_decision if decision.type_decision == 'REFUS' else "",
                 decision.code_decision if accord else "", _d(decision.date_decision)]
    else:
        ligne = ["", "", "", demande.code_demande or "", "", "", ""]
    el.append(_grille([["Montant mensuel", "Nb de mois", "Montant total", "Code demande", "Code refus",
                        "Code accord", "Date"], ligne], [2.8 * cm, 2.4 * cm, 2.6 * cm, 2.4 * cm, 2.3 * cm, 2.3 * cm, 3.2 * cm]))
    el.append(Spacer(1, 4))
    el.append(_grille([
        [_p("<b>Historique des aides ASE des 12 derniers mois</b>", st), _p("<b>Autres aides sollicitées</b>", st)],
        [_p(_txt(demande.historique_aides) or "-", st),
         _p((("Aides de droit commun : " + escape(", ".join(demande.aides_prealables_sollicitees)) + "<br/>")
             if demande.aides_prealables_sollicitees else "") + (_txt(demande.autres_aides_sollicitees) or "-"), st)],
    ], [9 * cm, 9 * cm]))

    # Évaluation sociale
    el.append(_section("ÉVALUATION SOCIALE", st))
    if ev:
        el.append(_p(f"<b>Code de la demande :</b> {escape(demande.code_demande or '')} – {escape(demande.libelle_demande)} &nbsp; "
                     f"<b>Avis du travailleur social :</b> {escape(demande.get_avis_ts_display())}", st))
        for titre, valeur in (("Situation familiale et problématique budgétaire", ev.situation_sociale),
                              ("Analyse de la situation", ev.analyse_problematique),
                              ("Justification de la demande", ev.justification_demande),
                              ("Plan d'action élaboré avec la famille", ev.plan_action),
                              ("Parcours d'insertion (16-21 ans)", ev.parcours_insertion),
                              ("Commentaire de la famille", ev.commentaire_familial)):
            if (valeur or "").strip():
                el += [_p(f"<b>{titre} :</b>", st), _p(_txt(valeur), st)]
        details = []
        if ev.adhesion_famille:
            details.append(f"<b>Adhésion de la famille :</b> {escape(ev.get_adhesion_famille_display())}")
        if ev.affectation_aide:
            details.append(f"<b>Affectation ciblée :</b> {escape(ev.affectation_aide)}")
        if details:
            el.append(_p(" &nbsp; ".join(details), st))

    # Budget
    el.append(_section("BUDGET MENSUEL DU MÉNAGE", st))
    if budget and (budget_afase.est_nouveau(budget.ressources) or budget_afase.est_nouveau(budget.charges)):
        t = budget.totaux
        aff = budget.affichage
        rl = [["Ressources mensuelles", "Demandeur", "Conjoint", "Autres"]]
        for titre, lignes_r in aff['ressources']:
            rl.append([_p(f"<b>{escape(titre)}</b>", st), "", "", ""])
            for lib, v in lignes_r:
                rl.append([_p(escape(lib), st), _e(v.get('demandeur')), _e(v.get('conjoint')), _e(v.get('autres'))])
        pc = t['par_colonne']
        rl.append(["Total des ressources mensuelles (1)", _e(pc.get('demandeur')), _e(pc.get('conjoint')), _e(pc.get('autres'))])
        el.append(_grille(rl, [9.3 * cm, 2.9 * cm, 2.9 * cm, 2.9 * cm], gras_derniere=True))
        el.append(Spacer(1, 4))
        cl = [["Charges mensuelles", "Payées", "Non payées"]]
        for titre, lignes_c in aff['charges']:
            cl.append([_p(f"<b>{escape(titre)}</b>", st), "", ""])
            for lib, v in lignes_c:
                cl.append([_p(escape(lib), st), _e(v.get('payee')), _e(v.get('non_payee'))])
        cl.append(["Total des charges (logement (2) + autres (3))", _e(t['charges_payees']), _e(t['charges_non_payees'])])
        el.append(_grille(cl, [12.2 * cm, 2.9 * cm, 2.9 * cm], gras_derniere=True))
        el.append(Spacer(1, 4))
        dettes = [["Dettes du ménage – créanciers", "Montant"]] + [[d.get('creancier', ''), _e(d.get('montant'))]
                                                                    for d in (budget.dettes or [])]
        bilan = [["Bilan budgétaire du ménage", ""], ["Total des ressources mensuelles (1)", _e(t['ressources'])],
                 ["Total des charges payées (2 + 3)", _e(t['charges_payees'])],
                 ["Nombre de personnes vivant au foyer", str(t['nb_personnes'])],
                 ["Reste à vivre (par jour et par personne)", _fr(t['reste_a_vivre'])]]
        el.append(Table([[_grille(dettes if len(dettes) > 1 else dettes + [["", ""]], [5.5 * cm, 2.5 * cm]),
                          _grille(bilan, [6.6 * cm, 2.6 * cm])]], colWidths=[8.4 * cm, 9.6 * cm],
                        style=[('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
        el.append(_p("<font size=7>Reste à vivre = (total des ressources mensuelles − total des charges payées) / nombre de "
                     "personnes / 30.</font>", st))
    elif budget:
        aff = budget.affichage
        el.append(_p("Budget saisi avec l'ancien formulaire : " + escape(", ".join(f"{k} {v} €" for k, v in aff['ressources']))
                     + " / charges : " + escape(", ".join(f"{k} {v} €" for k, v in aff['charges']))
                     + f" – reste à vivre {budget.reste_a_vivre} €", st))

    # Signature du demandeur + versement à un tiers
    tiers = decision.organisme_paiement if decision and decision.paiement_a == 'ORGANISME' else ""
    bloc = [_section("DATE ET SIGNATURE DU DEMANDEUR", st),
            _grille([[f"Date : {_d(demande.date_signature_demandeur)}", "Signature du demandeur"], ["", "\n\n\n"]],
                    [9 * cm, 9 * cm], entete=False),
            Spacer(1, 4),
            _p("<b>Autorisation de versement à un tiers (le cas échéant)</b>", st),
            _p(f"Je soussigné(e) {escape(dem.get_civilite_display())} {escape(dem.prenom)} {escape(dem.nom.upper())} autorise, "
               f"à titre exceptionnel, que l'aide financière soit versée sur le compte bancaire de : "
               f"{escape(tiers) or '..............................................'}", st),
            _grille([["Signature du demandeur pour le versement à un tiers"], ["\n\n"]], [18 * cm], entete=False)]
    el.append(KeepTogether(bloc))

    # Justificatifs
    el.append(_section("JUSTIFICATIFS OBLIGATOIRES JOINTS À LA DEMANDE", st))
    types = set(demande.pieces_justificatives.filter(document_ged__isnull=False).values_list('type_piece', flat=True))
    el.append(_p("<br/>".join(
        f"{COCHE if types & set(PIECES_EQUIVALENTES.get(code, (code,))) else VIDE} {escape(lib)}"
        for code, lib in PIECES_REQUISES_AFASE), st))

    # Signatures du travailleur social et du cadre
    qualites = " &nbsp; ".join(f"{COCHE if demande.qualite_ts == c else VIDE} {escape(l)}"
                               for c, l in demande.QUALITES_TS)
    decideur = decision.decide_par if decision else None
    el.append(KeepTogether([
        _section("DATE ET SIGNATURE DU TRAVAILLEUR SOCIAL ET DU CADRE", st),
        _p(qualites, st),
        _grille([[f"Travailleur social : {_nom(ts)}", f"Cadre : {_nom(decideur)}"],
                 [f"Date : {_d(demande.date_creation)}", f"Décision du : {_d(decision.date_decision) if decision else ''}"],
                 ["Signature et tampon\n\n\n", "Signature et tampon\n\n\n"]], [9 * cm, 9 * cm], entete=False),
    ]))
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer


# =============================================================================
# NOTIFICATION DE LA DÉCISION À L'USAGER
# =============================================================================

def texte_refus(decision):
    from AidFi.models.m_referentiel import MotifRefusAFASE
    m = MotifRefusAFASE.objects.filter(code=decision.code_decision).first()
    texte = (m.texte_notification if m and m.texte_notification else (m.libelle if m else decision.libelle_decision)) or ""
    return texte.replace("{precision}", decision.precision_notification or "(à préciser)")


def notification_pdf(demande):
    from AidFi.models.m_referentiel import ParametresAides
    decision = demande.decision
    p = ParametresAides.actuels()
    dem = demande.demandeur or demande.beneficiaire
    mds = demande.mds
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=3.5 * cm,
                            bottomMargin=2 * cm, title=f"Notification AFASE {demande.pk}", author="CID")
    st = get_ditas_styles()
    el = []
    if mds:
        el += [_p(f"<b>{escape(mds.nom)}</b><br/>{_txt(mds.adresse)}<br/>{escape(mds.code_postal)} {escape(mds.ville)}", st),
               Spacer(1, 0.5 * cm)]
    el += [Table([["", _p(f"{escape(dem.get_civilite_display())} {escape(dem.prenom)} {escape(dem.nom.upper())}<br/>"
                          f"{_txt(dem.adresse)}<br/>{escape(dem.code_postal)} {escape(dem.ville)}", st)]],
                 colWidths=[9 * cm, 8 * cm]),
           Spacer(1, 0.8 * cm),
           _p(f"{escape(mds.ville) if mds else ''}, le {_d(decision.date_decision)}", st), Spacer(1, 0.4 * cm),
           _p(f"<b>Objet :</b> votre demande d'allocation financière de l'aide sociale à l'enfance (dossier n° {demande.pk})", st),
           Spacer(1, 0.5 * cm), _p(f"{'Monsieur' if dem.civilite == 'M.' else 'Madame'},", st), Spacer(1, 0.3 * cm)]
    date_demande = _d(demande.date_signature_demandeur or demande.date_creation)
    from AidFi.services.afase_recours import recours_origine
    recours = recours_origine(demande)
    suite = (f"Suite à votre demande du {date_demande} et à votre recours du {_d(recours.date_recours)}"
             if recours else f"Suite à votre demande du {date_demande}")
    enfants = ", ".join(str(e) for e in demande.enfants.filter(concerne=True)) or "vos enfants"
    if decision.type_decision == 'ACCORD':
        total = (decision.montant_accorde or 0) * (decision.duree_accordee or 1)
        versement = (f"Elle sera versée à {escape(decision.organisme_paiement)}, comme vous l'avez autorisé."
                     if decision.paiement_a == 'ORGANISME' and decision.organisme_paiement
                     else "Elle sera versée sur votre compte bancaire.")
        corps = [
            f"{suite}, j'ai le plaisir de vous informer qu'une allocation financière de "
            f"l'aide sociale à l'enfance vous est accordée pour {escape(enfants)} :",
            f"<b>{_fr(decision.montant_accorde)} par mois pendant {decision.duree_accordee} mois</b> (versement mensuel), "
            f"soit {_fr(total)} au total, au titre de : <b>{escape(decision.libelle_decision or '')}</b>.",
            versement,
        ]
    else:
        corps = [f"{suite}, j'ai le regret de vous informer que je ne peux pas y donner "
                 f"une suite favorable, pour le motif suivant :",
                 f"<b>{escape(texte_refus(decision))}</b>"]
        # La motivation saisie par le cadre reste interne : seul le texte du code de refus (et sa précision)
        # est adressé à l'usager.
    if p.fondement_juridique:
        corps.append(f"<font size=8>Décision prise en application des textes suivants : {escape(p.fondement_juridique)}</font>")
    if p.texte_voies_recours:
        corps.append(f"<b>Voies et délais de recours :</b> {escape(p.texte_voies_recours)}")
    corps.append(f"Je vous prie d'agréer, {'Monsieur' if dem.civilite == 'M.' else 'Madame'}, l'expression de mes salutations distinguées.")
    for c in corps:
        el += [_p(c, st), Spacer(1, 0.3 * cm)]
    el += [Spacer(1, 0.6 * cm),
           Table([["", _p(f"Pour le Président du Conseil départemental<br/>et par délégation,<br/><br/>"
                          f"{escape(_nom(decision.decide_par))}", st)]], colWidths=[9 * cm, 8 * cm])]
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer
