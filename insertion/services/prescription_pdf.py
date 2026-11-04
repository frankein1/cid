# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/services/prescription_pdf.py
"""
Fiche de liaison (prescription) imprimable, à signer par le bénéficiaire et le prescripteur, puis à adresser
au porteur : tronc commun, freins, diagnostic et objectifs, réponses aux questions propres à l'action,
pièces jointes, consentement. Les réponses à accès restreint n'y figurent que pour les agents qui les voient.
"""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from AidFi.services.afase_pdf import draw_page_template
from insertion.services.contrat_pdf import BORD, _case, _d, _doc, _enfants, _nom, _oui, _rubrique, _styles, _t


def _reponse(q, valeur):
    if not valeur:
        return "—"
    if q.type_reponse == q.CHOIX_MULTIPLE:
        return ", ".join(v for v in valeur.split("\n") if v)
    if q.type_reponse == q.DATE and len(valeur) == 10:
        return f"{valeur[8:10]}/{valeur[5:7]}/{valeur[:4]}"
    return valeur


def fiche_pdf(p, restreintes=True):
    b, a = p.beneficiaire, p.action
    buffer = BytesIO()
    doc = _doc(buffer, f"Prescription {p.numero}")
    st = _styles()
    el = [Paragraph("Fiche de liaison – prescription", st["TitreOfficiel"]),
          Paragraph(f"<b>{escape(a.libelle)}</b> ({escape(a.code)}) · n° {p.numero} · du {_d(p.date_prescription)}",
                    st["Normal"]), Spacer(1, 0.4 * cm)]
    el += _rubrique("L'action", [("Porteur", a.porteur or "—"), ("Type", a.type_action.libelle),
                                 ("Adresser à", ", ".join(a.liste_destinataires) or "—")], st)
    el += _rubrique("Le prescripteur", [("Nom", _nom(p.prescripteur)), ("MDS", p.mds.nom if p.mds else "—"),
                                        ("Pôle insertion", p.pole.nom if p.pole else "—")], st)
    el += _rubrique("Le bénéficiaire", [
        ("Nom, prénom", f"{b.get_civilite_display()} {b.nom.upper()} {b.prenom}"
         + (f" (né(e) {b.nom_naissance})" if b.nom_naissance else "")),
        ("Né(e) le", _d(b.date_naissance)), ("Adresse", f"{b.adresse}, {b.code_postal} {b.ville}"),
        ("Téléphone, courriel", " · ".join(x for x in [b.telephone_mobile, b.telephone_fixe, b.email] if x) or "—"),
        ("N° allocataire", b.numero_caf or "—"),
        ("Situation familiale", b.get_marital_status_display() if b.marital_status else "—"),
        ("Enfants au foyer", _enfants(b)),
    ], st)
    el += _rubrique("Situation", [
        ("RSA", p.get_situation_rsa_display() if p.situation_rsa else "—"),
        ("Contrat", f"n° {p.contrat.numero}" + (f", jusqu'au {_d(p.contrat.date_fin)}" if p.contrat.date_fin else "")
         if p.contrat_id else "aucun"),
        ("France Travail", ("inscrit(e)" + (f", identifiant {p.identifiant_france_travail}"
                                            if p.identifiant_france_travail else "")) if p.inscrit_france_travail
         else "non inscrit(e)"),
        ("RQTH · QPV", f"RQTH : {_oui(p.rqth)} · QPV : {_oui(p.qpv)}"),
        ("Qualification", p.qualification), ("Sans activité depuis", p.inactivite),
        ("Freins", ", ".join(p.libelles_freins) or "—"),
    ], st)
    el += _rubrique("L'orientation", [
        ("Orientation", p.get_demande_par_display()), ("Diagnostic", p.diagnostic),
        ("Avis motivé", p.avis_motive), ("Objectifs", p.objectifs),
    ], st)
    lignes = []
    reponses = {r.question_id: r.valeur for r in p.reponses.all()}
    for q in a.questions.all():
        if q.restreinte and not restreintes:
            lignes.append((q.libelle, "réponse à accès restreint"))
        else:
            lignes.append((q.libelle, _reponse(q, reponses.get(q.pk, ""))))
    if lignes:
        el += _rubrique("Questions propres à l'action", lignes, st)
    if a.liste_pieces:
        el += _rubrique("Pièces jointes", [_case(x in p.pieces_fournies) + escape(x) for x in a.liste_pieces], st)
    el += _rubrique("Consentement", [
        _case(p.consentement) + "J'accepte que les informations de cette fiche soient transmises au porteur de "
        "l'action et au pôle insertion, pour l'organisation de mon parcours."], st)
    sig = Table([[Paragraph("<b>Le bénéficiaire</b>", st["Normal"]), Paragraph("<b>Le prescripteur</b>", st["Normal"])],
                 [Paragraph(f"Le {_d(p.date_signature)}", st["Normal"]),
                  Paragraph(f"{_t(_nom(p.prescripteur))}, le {_d(p.date_signature)}", st["Normal"])],
                 ["\n\n\n", ""]], colWidths=[8.7 * cm, 8.7 * cm])
    sig.setStyle(TableStyle([('BOX', (0, 0), (0, -1), 0.5, BORD), ('BOX', (1, 0), (1, -1), 0.5, BORD)]))
    el.append(KeepTogether([sig]))
    el += [Spacer(1, 0.4 * cm)]
    el += _rubrique("Retour du porteur (à compléter et à renvoyer au prescripteur)", [
        f"Premier rendez-vous le …/…/……  {_case()}présent(e)  {_case()}absent(e)  {_case()}excusé(e)  "
        f"{_case()}reconvoqué(e)",
        f"{_case()}Intégré(e) le …/…/……   {_case()}Non intégré(e) – motif : ………………………………………………",
        f"Sortie le …/…/…… – motif : ………………………………   Réorientation : {_case()}ASI  {_case()}autre dispositif  "
        f"{_case()}France Travail",
    ], st)
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer
