# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# protection_enfance/services/ip_pdf.py
"""
Documents d'une IP, produits par CID à partir de ce qui est saisi (pas de ressaisie sous Word) :
  - courrier de convocation des parents, puis LRAR de relance ;
  - rapport d'évaluation avec visas (cadre, AS, inspecteur), imprimable pour le procureur
    ou un autre département ;
  - courrier de saisine du procureur.
L'identité du déclarant n'apparaît JAMAIS dans ces documents.
"""
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles
from protection_enfance.models.m_evaluation import ActionIP


def _nom(u):
    return (u.get_full_name() or u.username) if u else "-"


def _txt(valeur):
    """Texte saisi → paragraphe reportlab (échappement + retours à la ligne)."""
    return escape(valeur or "").replace("\n", "<br/>")


def _date(d, heure=False):
    if not d:
        return "-"
    if hasattr(d, 'hour'):
        d = timezone.localtime(d)
        return d.strftime("%d/%m/%Y à %H:%M" if heure else "%d/%m/%Y")
    return d.strftime("%d/%m/%Y")


def _doc(buffer, titre):
    return SimpleDocTemplate(buffer, pagesize=A4, topMargin=3.5 * cm, bottomMargin=2 * cm,
                             leftMargin=2 * cm, rightMargin=2 * cm, title=titre, author="CID")


def _enfants(ip):
    return ", ".join(f"{e.prenom} {e.nom.upper()}" + (f" (né(e) le {_date(e.date_naissance)})" if e.date_naissance else "")
                     for e in ip.enfants.all()) or "-"


def _bloc_mds(ip, st):
    m = ip.mds
    if not m:
        return []
    return [Paragraph(f"<b>{escape(m.nom)}</b><br/>{_txt(m.adresse)}<br/>{escape(m.code_postal)} {escape(m.ville)}"
                      + (f"<br/>Tél. {escape(m.telephone)}" if m.telephone else ""), st["Normal"]),
            Spacer(1, 0.6 * cm)]


def _destinataire(ip, st):
    f = ip.famille
    if f:
        lignes = f"{escape(f.get_civilite_display())} {escape(f.prenom)} {escape(f.nom.upper())}<br/>{_txt(f.adresse)}<br/>{escape(f.code_postal)} {escape(f.ville)}"
    else:
        lignes = f"Famille {escape(ip.famille_libelle)}<br/>{_txt(ip.famille_adresse)}"
    t = Table([["", Paragraph(lignes, st["Normal"])]], colWidths=[9 * cm, 8 * cm])
    return [t, Spacer(1, 0.8 * cm)]


def _signatures_binome(ip, st):
    noms = [_nom(u) for u in ip.binome] or ["Le travailleur social"]
    t = Table([noms, ["\n\n\n"] * len(noms)], colWidths=[8.5 * cm] * len(noms))
    t.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]))
    return [Spacer(1, 0.8 * cm), t]


# =============================================================================
# COURRIERS AUX PARENTS
# =============================================================================

def courrier_pdf(action: ActionIP):
    """Courrier d'une convocation à une audition (un par destinataire) ; anciens courriers : modèle d'origine."""
    if action.destinataire_id:
        return _convocation_audition_pdf(action)
    return _courrier_ancien_pdf(action)


def _salutation(adultes):
    civ = {a.civilite for a in adultes}
    return "Madame, Monsieur," if len(civ) > 1 else ("Monsieur," if civ == {'M.'} else "Madame,")


def _convocation_audition_pdf(action):
    from protection_enfance.models import ConvoqueIP
    from protection_enfance.services.ip_famille import hebergeants_meme_adresse
    ip, dest = action.ip, action.destinataire
    enfants = list(action.enfants_concernes.all())
    pour_enfants = bool(enfants)
    lrar = action.type_action == 'LRAR'
    adultes_entete = hebergeants_meme_adresse(dest) if pour_enfants else [dest]
    buffer = BytesIO()
    doc = _doc(buffer, f"{'LRAR' if lrar else 'Convocation'} {ip.numero} – {dest.nom}")
    st = get_ditas_styles()
    el = _bloc_mds(ip, st)
    lignes = " et ".join(escape(a.nom_complet) for a in adultes_entete)
    lignes += f"<br/>{escape(dest.adresse)}<br/>{escape(dest.code_postal)} {escape(dest.ville)}"
    el += [Table([["", Paragraph(lignes, st["Normal"])]], colWidths=[9 * cm, 8 * cm]), Spacer(1, 0.8 * cm),
           Paragraph(f"{escape(ip.mds.ville) if ip.mds else ''}, le {_date(action.date)}", st["Normal"]),
           Spacer(1, 0.4 * cm)]
    if lrar:
        el.append(Paragraph(f"<b>Lettre recommandée avec accusé de réception"
                            f"{' n° ' + escape(action.numero_lrar) if action.numero_lrar else ''}</b>", st["Normal"]))
    el += [Paragraph(f"<b>Objet :</b> convocation – information préoccupante réf. {ip.numero}", st["Normal"]),
           Spacer(1, 0.5 * cm)]

    quand = f"le <b>{_date(action.date_rdv_propose, heure=True)}</b>"
    lieu = (f"{escape(ip.mds.nom)}, {_txt(ip.mds.adresse)}, {escape(ip.mds.code_postal)} {escape(ip.mds.ville)}"
            if ip.mds else "la Maison départementale de la solidarité")
    noms_enfants = ", ".join(f"{e.prenom} {e.nom.upper()}" for e in enfants)
    pluriel = len(enfants) > 1
    # Date de la convocation précédente, pour une LRAR ou un report
    precedent = ConvoqueIP.objects.filter(suite=action.rdv).select_related('action').first() if action.rdv_id else None
    date_prec = _date(precedent.action.date_rdv_propose or precedent.action.date, heure=True) if precedent else None

    corps = [_salutation(adultes_entete)]
    if pour_enfants:
        sujet = f"{'vos enfants' if pluriel else 'votre enfant'} {escape(noms_enfants)}"
        if lrar:
            corps.append(f"{sujet[0].upper()}{sujet[1:]} {'ne se sont pas présentés' if pluriel else 'ne s’est pas présenté(e)'}"
                         + (f" à la convocation du {date_prec}" if date_prec else " à la précédente convocation") + ".")
        elif action.report_convenu:
            corps.append("Comme convenu avec vous, nous vous adressons la nouvelle date de convocation.")
        corps.append(f"Dans le cadre de l'information préoccupante, {sujet} {'sont convoqués' if pluriel else 'est convoqué(e)'} "
                     f"{quand}, à {lieu}.")
        corps.append("Les enfants sont reçus un par un par les professionnels ; merci de les accompagner. "
                     "Les adultes qui les accompagnent patientent en salle d'attente." if pluriel else
                     "L'enfant est reçu seul par les professionnels ; merci de l'accompagner. "
                     "L'adulte qui l'accompagne patiente en salle d'attente.")
    else:
        if lrar:
            corps.append("Vous ne vous êtes pas présenté(e)"
                         + (f" à la convocation du {date_prec}" if date_prec else " à la précédente convocation") + ".")
        elif action.report_convenu:
            corps.append("Comme convenu avec vous, nous vous adressons la nouvelle date de convocation.")
        corps.append(f"Dans le cadre de l'information préoccupante concernant {escape(_enfants(ip))}, "
                     f"vous êtes convoqué(e) {quand}, à {lieu}.")
    if lrar:
        corps.append("Nous vous rappelons que cette évaluation est obligatoire. À défaut de pouvoir la mener avec vous, "
                     "le rapport sera établi avec les seuls éléments recueillis et transmis à l'inspecteur enfance "
                     "famille du Département, qui pourra décider de saisir l'autorité judiciaire.")
    corps += ["En cas d'empêchement, merci de nous contacter au plus vite pour convenir d'une autre date.",
              "Nous vous prions d'agréer, " + _salutation(adultes_entete).rstrip(',') + ", nos salutations distinguées."]
    for p in corps:
        el += [Paragraph(p, st["Normal"]), Spacer(1, 0.3 * cm)]
    el += _signatures_binome(ip, st)
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer


def _courrier_ancien_pdf(action: ActionIP):
    ip = action.ip
    buffer = BytesIO()
    lrar = action.type_action == 'LRAR'
    doc = _doc(buffer, f"{'LRAR' if lrar else 'Convocation'} {ip.numero}")
    st = get_ditas_styles()
    el = _bloc_mds(ip, st) + _destinataire(ip, st)
    lieu_date = f"{ip.mds.ville if ip.mds else ''}, le {_date(action.date)}"
    el.append(Paragraph(lieu_date, st["Normal"]))
    el.append(Spacer(1, 0.4 * cm))
    if lrar:
        el.append(Paragraph(f"<b>Lettre recommandée avec accusé de réception"
                            f"{' n° ' + escape(action.numero_lrar) if action.numero_lrar else ''}</b>", st["Normal"]))
    el.append(Paragraph(f"<b>Objet :</b> évaluation de la situation de vos enfants – réf. {ip.numero}", st["Normal"]))
    el.append(Spacer(1, 0.5 * cm))

    rdv = (f"le <b>{_date(action.date_rdv_propose, heure=True)}</b>" if action.date_rdv_propose
           else "à une date à convenir en appelant la MDS")
    adresse = f"{escape(ip.mds.nom)}, {_txt(ip.mds.adresse)}, {escape(ip.mds.code_postal)} {escape(ip.mds.ville)}" if ip.mds else "la MDS"
    if not lrar:
        corps = [
            "Madame, Monsieur,",
            f"Les services du Département ont été destinataires d'une information concernant "
            f"{'votre enfant' if ip.enfants.count() == 1 else 'vos enfants'} : {escape(_enfants(ip))}.",
            "Comme le prévoit la loi, une évaluation de la situation familiale est engagée. Elle est menée par "
            "deux professionnels de la Maison départementale de la solidarité, avec vous et vos enfants.",
            f"Nous vous proposons de nous rencontrer {rdv}, à {adresse}, en présence de vos enfants.",
            "Si cette date ne vous convient pas, merci de nous contacter au plus vite pour en convenir d'une autre.",
            "Nous vous prions d'agréer, Madame, Monsieur, nos salutations distinguées.",
        ]
    else:
        precedent = ip.actions.filter(type_action='CONVOCATION', date__lt=action.date).order_by('-date').first()
        corps = [
            "Madame, Monsieur,",
            (f"Par courrier du {_date(precedent.date)}, nous vous avions proposé un rendez-vous"
             if precedent else "Nous vous avons proposé un rendez-vous")
            + f" dans le cadre de l'évaluation de la situation de {escape(_enfants(ip))}. "
              "Nous n'avons pas pu vous rencontrer.",
            f"Nous vous proposons un nouveau rendez-vous {rdv}, à {adresse}, en présence de vos enfants.",
            "Nous vous rappelons que cette évaluation est obligatoire. À défaut de pouvoir la mener avec vous, "
            "le rapport sera établi avec les seuls éléments recueillis et transmis à l'inspecteur enfance famille "
            "du Département, qui pourra décider de saisir l'autorité judiciaire.",
            "Nous restons à votre disposition pour convenir d'un autre horaire.",
            "Nous vous prions d'agréer, Madame, Monsieur, nos salutations distinguées.",
        ]
    for p in corps:
        el += [Paragraph(p, st["Normal"]), Spacer(1, 0.3 * cm)]
    el += _signatures_binome(ip, st)
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer


# =============================================================================
# RAPPORT D'ÉVALUATION
# =============================================================================

def rapport_pdf(ip):
    from protection_enfance.services.ip_circuit import rapport_de
    rapport = rapport_de(ip)
    buffer = BytesIO()
    doc = _doc(buffer, f"Rapport d'évaluation {ip.numero}")
    st = get_ditas_styles()
    el = [
        Paragraph("RAPPORT D'ÉVALUATION D'INFORMATION PRÉOCCUPANTE", st["TitreOfficiel"]),
        Paragraph(f"<b>Référence :</b> {ip.numero} &nbsp;&nbsp; <b>MDS :</b> {escape(str(ip.mds or '-'))}", st["Normal"]),
        Paragraph(f"<b>Famille :</b> {escape(ip.libelle_famille)}", st["Normal"]),
        Paragraph(f"<b>Enfant(s) :</b> {escape(_enfants(ip))}", st["Normal"]),
        Paragraph(f"<b>Origine de l'IP :</b> {escape(ip.get_origine_display())} – déclarant non mentionné "
                  f"(identité conservée par la CRIP)", st["Normal"]),
        Paragraph(f"<b>Reçue par la CRIP le</b> {_date(ip.date_reception_crip)} – <b>échéance</b> "
                  f"{_date(ip.date_echeance)}", st["Normal"]),
        Paragraph(f"<b>Binôme :</b> {escape(', '.join(_nom(u) for u in ip.binome) or '-')}", st["Normal"]),
    ]
    if ip.autre_departement:
        el.append(Paragraph(f"<b>Autre département concerné :</b> {escape(ip.autre_departement)}", st["Normal"]))

    el.append(Paragraph("Déroulé de l'évaluation", st["SectionHeader"]))
    lignes = [["Date", "Démarche", "Résultat"]]
    for a in ip.actions.select_related('enfant', 'destinataire').prefetch_related('convoques').order_by('date'):
        libelle = a.get_type_action_display() + (f" – {a.enfant}" if a.enfant_id else "")
        if a.destinataire_id:
            libelle += f" à {a.destinataire.nom_complet}"
        if a.numero_lrar:
            libelle += f" (n° {a.numero_lrar})"
        if a.convoques.all():
            libelle += " – " + "; ".join(f"{cv.personne.prenom} {cv.personne.nom.upper()} : "
                                         f"{cv.get_presence_display().lower()}" for cv in a.convoques.all())
        lignes.append([_date(a.date, heure=True), Paragraph(escape(libelle), st["Normal"]), a.get_resultat_display()])
    if len(lignes) == 1:
        lignes.append(["-", "Aucune démarche enregistrée", ""])
    t = Table(lignes, colWidths=[3.6 * cm, 9.4 * cm, 4 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    el.append(t)
    if rapport.non_cooperation:
        el += [Spacer(1, 0.3 * cm), Paragraph(
            "<b>La famille n'a pas coopéré à l'évaluation malgré l'envoi d'une lettre recommandée. "
            "Le rapport est établi avec les éléments recueillis.</b>", st["Normal"])]

    for _, titre, texte in rapport.rubriques:
        el += [Paragraph(escape(titre), st["SectionHeader"]), Paragraph(_txt(texte) or "-", st["Normal"])]

    el.append(Paragraph("Conclusion pour chaque enfant", st["SectionHeader"]))
    for e in ip.enfants.prefetch_related('dangers_constates'):
        dangers = ", ".join(str(d) for d in e.dangers_constates.all())
        el.append(Paragraph(f"<b>{escape(str(e))}</b>{' (' + str(e.age) + ' ans)' if e.age is not None else ''} : "
                            f"<b>{escape(e.get_conclusion_display() or 'non renseignée')}</b>"
                            + (f" – {escape(dangers)}" if dangers else ""), st["Normal"]))
        if e.conclusion_commentaire:
            el.append(Paragraph(_txt(e.conclusion_commentaire), st["Normal"]))
        el.append(Spacer(1, 0.2 * cm))
    el += [Paragraph("Préconisations", st["SectionHeader"]),
           Paragraph(f"<b>{escape(rapport.get_preconisation_display() or '-')}</b>", st["Normal"]),
           Paragraph(_txt(rapport.preconisation_detail), st["Normal"]), Spacer(1, 0.6 * cm)]

    avis = ""
    if rapport.avis_pief:
        avis = rapport.get_avis_pief_display() + (f"\n{rapport.commentaire_pief}" if rapport.commentaire_pief else "")
    vis = Table([
        ["Le cadre de la MDS", "L'assistant(e) social(e)", "L'inspecteur enfance famille"],
        [f"{_nom(rapport.visa_cadre_par)}\n{_date(rapport.date_visa_cadre)}" if rapport.visa_cadre_par else "",
         f"{_nom(rapport.visa_as_par)}\n{_date(rapport.date_visa_as)}" if rapport.visa_as_par else "",
         Paragraph(_txt(f"{_nom(rapport.visa_pief_par)} – {_date(rapport.date_visa_pief)}\n{avis}"), st["Normal"])
         if rapport.visa_pief_par else ""],
        ["\n\n", "", ""],
    ], colWidths=[5.6 * cm] * 3)
    vis.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 8),
                             ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    if rapport.date_synthese:
        el.append(Paragraph(f"Rapport vu en réunion de synthèse le {_date(rapport.date_synthese)}.", st["Normal"]))
        el.append(Spacer(1, 0.3 * cm))
    el.append(vis)
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer


# =============================================================================
# SAISINE DU PROCUREUR
# =============================================================================

def saisine_pdf(s):
    ip = s.ip
    buffer = BytesIO()
    doc = _doc(buffer, f"Saisine du procureur {ip.numero}")
    st = get_ditas_styles()
    el = _bloc_mds(ip, st) + [
        Paragraph("Monsieur ou Madame le Procureur de la République", st["Normal"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Objet :</b> saisine concernant des mineurs en danger – réf. {ip.numero}", st["Normal"]),
        Spacer(1, 0.4 * cm),
        Paragraph(f"<b>Famille :</b> {escape(ip.libelle_famille)}", st["Normal"]),
        Paragraph(f"<b>Adresse :</b> {_txt(ip.famille.adresse + ' ' + ip.famille.code_postal + ' ' + ip.famille.ville) if ip.famille else _txt(ip.famille_adresse)}", st["Normal"]),
        Paragraph(f"<b>Enfant(s) :</b> {escape(_enfants(ip))}", st["Normal"]),
        Spacer(1, 0.4 * cm),
        Paragraph("<b>Motif de la saisine</b>" + (" – <b>danger grave et imminent</b>" if s.danger_imminent else ""), st["Normal"]),
        Paragraph(_txt(s.motif), st["Normal"]),
        Spacer(1, 0.4 * cm),
        Paragraph(f"Proposée par {escape(_nom(s.propose_par))} le {_date(s.date_proposition)} ; "
                  f"décision du cadre : {escape(_nom(s.cadre))} le {_date(s.date_decision_cadre)}"
                  + (f" ; validée par l'inspecteur enfance famille {escape(_nom(s.inspecteur))} le {_date(s.date_decision_pief)}"
                     if s.inspecteur else " ; saisine directe par le cadre (danger grave et imminent)")
                  + ".", st["Normal"]),
    ]
    if hasattr(ip, 'rapport') and ip.rapport.date_soumission:
        el += [Spacer(1, 0.3 * cm), Paragraph("Le rapport d'évaluation est joint.", st["Normal"])]
    sig = Table([["Le cadre de la MDS", "L'inspecteur enfance famille"], ["\n\n\n", ""]], colWidths=[8.5 * cm] * 2)
    sig.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]))
    el += [Spacer(1, 0.8 * cm), sig]
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer
