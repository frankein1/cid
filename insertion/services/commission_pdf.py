# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/services/commission_pdf.py
"""
Documents de la commission de réorientation : ordre du jour (dossiers par MDS), relevé de décisions
(participants, décision de chaque dossier) et notification de la décision au bénéficiaire
(modèle de courrier RSA_NOTIFICATION_REORIENTATION, modifiable en administration).
"""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles
from insertion.models import DemandeReorientation as D
from insertion.services.contrat_pdf import BORD, GRIS, _courrier, _d, _nom, _t

ENTETE = ('BACKGROUND', (0, 0), (-1, 0), GRIS)


def _doc(buffer, titre):
    return SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=3.2 * cm, bottomMargin=1.8 * cm,
                             leftMargin=1.5 * cm, rightMargin=1.5 * cm, title=titre, author="CID")


def _styles():
    st = get_ditas_styles()
    st["Normal"].fontSize, st["Normal"].leading = 8.5, 10.5
    return st


def _entete(c, titre, st):
    quand = f"{_d(c.date)}" + (f" à {c.heure:%H:%M}" if c.heure else "") + (f" – {escape(c.lieu)}" if c.lieu else "")
    return [Paragraph(titre, st["TitreOfficiel"]),
            Paragraph(f"<b>{escape(c.pole.nom)}</b> · commission du {quand}", st["Normal"]), Spacer(1, 0.4 * cm)]


def _demandes(c):
    return (c.demandes.exclude(statut=D.ANNULEE)
            .select_related('beneficiaire', 'mds', 'referent', 'organisme_propose', 'organisme_retenu')
            .order_by('mds__nom', 'beneficiaire__nom'))


def _table(data, largeurs):
    t = Table(data, colWidths=largeurs, repeatRows=1)
    t.setStyle(TableStyle([ENTETE, ('GRID', (0, 0), (-1, -1), 0.5, BORD), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    return t


def _proposee(d):
    return d.orientation_libelle


def ordre_du_jour_pdf(c):
    buffer = BytesIO()
    doc = _doc(buffer, f"Ordre du jour {c.numero}")
    st = _styles()
    el = _entete(c, "Commission de réorientation – ordre du jour", st)
    P = lambda x: Paragraph(_t(x), st["Normal"])   # noqa: E731
    data = [[Paragraph(f"<b>{x}</b>", st["Normal"]) for x in
             ("MDS", "Bénéficiaire", "Référent", "Orientation proposée", "Motif", "Freins", "Personne")]]
    for d in _demandes(c):
        b = d.beneficiaire
        nom = f"{b.nom.upper()} {b.prenom}<br/>né(e) le {_d(b.date_naissance)}" + (
            f"<br/><i>{d.nb_ajournements} ajournement(s)</i>" if d.nb_ajournements else "")
        data.append([P(d.mds.nom if d.mds else ""), Paragraph(nom, st["Normal"]), P(_nom(d.referent)), P(_proposee(d)),
                     P(d.motif), P(", ".join(d.libelles_freins)), P(d.get_avis_personne_display())])
    if len(data) == 1:
        el.append(Paragraph("Aucun dossier inscrit.", st["Normal"]))
    else:
        el.append(_table(data, [2.6 * cm, 3.4 * cm, 2.8 * cm, 4 * cm, 7.6 * cm, 3.6 * cm, 2.6 * cm]))
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer


def releve_pdf(c):
    buffer = BytesIO()
    doc = _doc(buffer, f"Relevé de décisions {c.numero}")
    st = _styles()
    el = _entete(c, "Commission de réorientation – relevé de décisions", st)
    presents = ", ".join(_nom(u) for u in c.participants.order_by('last_name')) or "—"
    el += [Paragraph(f"<b>Participants :</b> {escape(presents)}", st["Normal"])]
    if c.participants_externes:
        el.append(Paragraph(f"<b>Autres participants :</b> {_t(c.participants_externes)}", st["Normal"]))
    if c.observations:
        el.append(Paragraph(f"<b>Observations :</b> {_t(c.observations)}", st["Normal"]))
    el.append(Spacer(1, 0.3 * cm))
    P = lambda x: Paragraph(_t(x), st["Normal"])   # noqa: E731
    data = [[Paragraph(f"<b>{x}</b>", st["Normal"]) for x in
             ("MDS", "Bénéficiaire", "Orientation proposée", "Décision", "Nouveau référent RSA", "Date d'effet", "Motif")]]
    examens = {e.demande_id: e for e in c.examens.select_related('organisme_retenu')}
    lignes = list(_demandes(c)) if c.statut == c.PREPARATION else [
        e.demande for e in c.examens.select_related('demande__beneficiaire', 'demande__mds', 'demande__organisme_propose')
        .order_by('demande__mds__nom', 'demande__beneficiaire__nom')]
    for d in lignes:
        e = examens.get(d.pk)
        data.append([P(d.mds.nom if d.mds else ""), P(f"{d.beneficiaire.nom.upper()} {d.beneficiaire.prenom}"),
                     P(_proposee(d)), P(e.get_decision_display() if e else "à décider"),
                     P(e.organisme_retenu.nom if e and e.organisme_retenu else ""),
                     P(_d(e.date_effet) if e and e.date_effet else ""), P(e.motif if e else "")])
    el.append(_table(data, [2.6 * cm, 3.6 * cm, 4.2 * cm, 3.2 * cm, 4 * cm, 2.2 * cm, 6.8 * cm]))
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer


def notification_pdf(d):
    b = d.beneficiaire
    org = d.organisme_retenu
    valeurs = {"civilite_appel": "Monsieur" if b.civilite == 'M.' else "Madame",
               "beneficiaire": f"{b.prenom} {b.nom.upper()}", "date_commission": _d(d.date_decision),
               "organisme": org.nom if org else "", "date_effet": _d(d.date_effet) if d.date_effet else "",
               "coordonnees_organisme": " – ".join(x for x in [org.adresse if org else "",
                                                               f"{org.code_postal} {org.ville}".strip() if org else "",
                                                               org.telephone if org else ""] if x),
               "motif": d.motif_decision, "referent": _nom(d.referent), "mds": d.mds.nom if d.mds else "",
               "pole": d.pole.nom if d.pole else "", "signataire": _nom(d.decide_par)}
    conditions = {"si_acceptee": d.statut == D.ACCEPTEE, "si_refusee": d.statut == D.REFUSEE}
    pole = d.pole
    expediteur = (f"<b>{escape(pole.nom)}</b><br/>{_t(pole.adresse)}<br/>{escape(pole.code_postal)} {escape(pole.ville)}"
                  if pole else "")
    dest = (f"{escape(b.get_civilite_display())} {escape(b.prenom)} {escape(b.nom.upper())}<br/>{_t(b.adresse)}<br/>"
            f"{escape(b.code_postal)} {escape(b.ville)}")
    return _courrier(d, "RSA_NOTIFICATION_REORIENTATION", valeurs, conditions, expediteur, dest, d.date_decision,
                     f"Réorientation {d.numero}")
