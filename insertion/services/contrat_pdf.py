# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# insertion/services/contrat_pdf.py
"""
Documents du contrat RSA, produits à partir de ce qui est saisi dans CID :
  - le contrat imprimé, à signer par le bénéficiaire et le référent (rubriques de l'imprimé départemental,
    décision de la commission quand elle est prise) ;
  - la demande de certificat au médecin traitant (contrat santé), remise au bénéficiaire ;
  - la notification de la décision au bénéficiaire.
Les deux courriers suivent les Modèles de courriers (textes modifiables en administration).
"""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles
from insertion.models import ContratInsertion, ParametresRSA

GRIS = colors.HexColor("#f1f5f9")
BORD = colors.HexColor("#cbd5e1")


def _t(v):
    return escape("" if v is None else str(v)).replace("\n", "<br/>")


def _d(d):
    return d.strftime("%d/%m/%Y") if d else "…/…/……"


def _nom(u):
    return (u.get_full_name() or u.username) if u else "-"


def _case(coche=False):
    """Case à cocher : les polices standard des PDF n'ont pas les caractères ☐ ☑ (ZapfDingbats : ❏ et ✔)."""
    return f'<font name="ZapfDingbats">{"4" if coche else "o"}</font> '


def _oui(b):
    return "oui" if b else "non"


def _doc(buffer, titre):
    return SimpleDocTemplate(buffer, pagesize=A4, topMargin=3.5 * cm, bottomMargin=2 * cm, leftMargin=1.8 * cm,
                             rightMargin=1.8 * cm, title=titre, author="CID")


def _styles():
    st = get_ditas_styles()
    st["Normal"].fontSize, st["Normal"].leading = 9.5, 12
    return st


def _rubrique(titre, lignes, st):
    """Cadre titré : lignes = [(libellé, valeur)] ou [texte] (valeur sur toute la largeur)."""
    data = [[Paragraph(f"<b>{escape(titre)}</b>", st["Normal"]), ""]]
    for l in lignes:
        if isinstance(l, tuple):
            data.append([Paragraph(escape(l[0]), st["Normal"]), Paragraph(_t(l[1]) or "—", st["Normal"])])
        else:
            data.append([Paragraph(l, st["Normal"]), ""])
    t = Table(data, colWidths=[5.2 * cm, 12.2 * cm])
    style = [('SPAN', (0, 0), (-1, 0)), ('BACKGROUND', (0, 0), (-1, 0), GRIS), ('BOX', (0, 0), (-1, -1), 0.5, BORD),
             ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 3),
             ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]
    for i, l in enumerate(lignes, start=1):
        if not isinstance(l, tuple):
            style.append(('SPAN', (0, i), (-1, i)))
    t.setStyle(TableStyle(style))
    return [KeepTogether([t]), Spacer(1, 0.25 * cm)]


def _enfants(b):
    return ", ".join(f"{m['personne'].prenom} {m['personne'].nom.upper()} ({_d(m['personne'].date_naissance)})"
                     for m in b.reseau_familial() if m['type_lien'] == 'ENFANT' and m['vit_au_foyer']) or "—"


def contrat_pdf(c: ContratInsertion):
    p = ParametresRSA.courant()
    b = c.beneficiaire
    buffer = BytesIO()
    doc = _doc(buffer, f"{p.nom_contrat} {c.numero}")
    st = _styles()
    el = [Paragraph(f"{escape(p.nom_contrat)}", st["TitreOfficiel"]),
          Paragraph(f"<b>{escape(c.get_type_contrat_display())}</b> · n° {c.numero} · établi le {_d(c.date_etablissement)}"
                    f" · reçu au pôle le {_d(c.date_reception)}", st["Normal"]), Spacer(1, 0.4 * cm)]
    el += _rubrique("Le bénéficiaire", [
        ("Nom, prénom", f"{b.get_civilite_display()} {b.nom.upper()} {b.prenom}"),
        ("Né(e) le", _d(b.date_naissance)), ("Adresse", f"{b.adresse}, {b.code_postal} {b.ville}"),
        ("N° allocataire", b.numero_caf or "—"), ("Enfants au foyer", _enfants(b)),
    ], st)
    if c.conjoint_id or c.conjoint_situation:
        el += _rubrique("Le conjoint", [
            ("Nom, prénom", f"{c.conjoint.nom.upper()} {c.conjoint.prenom}" if c.conjoint_id else "—"),
            ("Situation", c.conjoint_situation), ("Opérateur", c.conjoint_operateur), ("Référent", c.conjoint_referent),
        ], st)
    el += _rubrique("Le référent", [("Nom", _nom(c.referent)), ("MDS", c.mds.nom if c.mds else "—"),
                                    ("Pôle insertion", c.pole.nom if c.pole else "—")], st)
    el += _rubrique("Diagnostic", [
        ("France Travail", ("inscrit(e)" + (f", identifiant {c.identifiant_france_travail}"
                                            if c.identifiant_france_travail else "")) if c.inscrit_france_travail
         else "non inscrit(e)"),
        ("Niveau d'études", c.get_niveau_etudes_display() if c.niveau_etudes else "—"), ("Formation", c.formation),
        ("Expérience", c.experience),
        ("Dernier emploi", " · ".join(x for x in [c.dernier_emploi, str(c.dernier_emploi_annee or ""),
                                                  c.dernier_emploi_duree] if x)),
        ("Emploi recherché", c.emploi_recherche),
        ("Français", f"parlé : {_oui(c.francais_parle)} · lu : {_oui(c.francais_lu)} · écrit : {_oui(c.francais_ecrit)}"),
        ("Mobilité", f"permis B : {_oui(c.permis_b)}" + (f" · autres : {c.autres_permis}" if c.autres_permis else "")
         + f" · véhiculé(e) : {_oui(c.vehicule)}"),
        ("Couverture maladie", f"base : {c.couverture_base or '—'} · complémentaire : {c.couverture_complementaire or '—'}"),
        ("Logement", " – ".join(x for x in [c.get_logement_display() if c.logement else "", c.logement_precision] if x)),
    ], st)
    incidences = [n for n, v in [("création d'activité", c.incidence_creation_activite),
                                 ("formation", c.incidence_formation), ("frais annexes", c.incidence_frais_annexes)] if v]
    el += _rubrique("Nature du contrat", [
        ("Nature", c.get_nature_display()), ("Incidence financière", ", ".join(incidences) or "aucune"),
        ("Activité", f"{c.heures_activite_hebdo} heures par semaine"),
        ("Durée proposée", f"{c.duree_proposee_mois} mois"),
        ("Aide aux transports", ", ".join(n for n, v in [("urbain", c.aide_transport_urbain),
                                                         ("interurbain", c.aide_transport_interurbain)] if v)
         or "non demandée"),
    ], st)
    el += _rubrique("La parole du bénéficiaire", [("Ma situation actuelle", c.parole_situation),
                                                   ("Ce que j'ai déjà fait", c.parole_deja_fait),
                                                   ("Ce que je souhaite faire", c.parole_souhaits)], st)
    el += _rubrique("Le référent", [("Objectifs", c.objectifs), ("Étapes", c.etapes),
                                    ("Observations", c.observations)], st)
    # Actions
    data = [[Paragraph(f"<b>{x}</b>", st["Normal"]) for x in ("Action", "Entrée", "Sortie", "Motif de sortie")]]
    for l in c.lignes.select_related('action'):
        libelle = _t(l.intitule) + (f"<br/><i>Non retenue : {_t(l.motif_non_retenue)}</i>" if l.non_retenue else "")
        data.append([Paragraph(libelle, st["Normal"]), _d(l.date_entree) if l.date_entree else "",
                     _d(l.date_sortie) if l.date_sortie else "", Paragraph(_t(l.motif_sortie), st["Normal"])])
    t = Table(data, colWidths=[8.4 * cm, 2.3 * cm, 2.3 * cm, 4.4 * cm], repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), GRIS), ('GRID', (0, 0), (-1, -1), 0.5, BORD),
                           ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('FONTSIZE', (0, 0), (-1, -1), 9)]))
    el += [Paragraph("<b>Actions</b>", st["Normal"]), Spacer(1, 0.1 * cm), t, Spacer(1, 0.3 * cm)]
    if c.certificat_obligatoire:
        el += _rubrique("Contrat santé", [
            "Le médecin traitant adresse un certificat médical au seul médecin du pôle insertion "
            f"({escape(c.get_certificat_mode_display().lower() or 'mode à préciser')}). "
            "Ni le référent ni la commission n'en connaissent le contenu.",
            ("Avis du médecin du pôle", c.get_avis_medical_display() if c.avis_medical else "en attente"),
        ], st)
    # Commission
    if c.decision:
        lignes = [("Décision", f"{c.get_decision_display()} le {_d(c.date_decision)}")]
        if c.date_fin:
            lignes.append(("Durée", f"{c.duree_validee_mois} mois, du {_d(c.date_debut)} au {_d(c.date_fin)}"))
        if c.motif_decision:
            lignes.append(("Motif", c.motif_decision))
        if c.decision_transport:
            lignes.append(("Aide aux transports", c.get_decision_transport_display()
                           + (f" ({c.get_motif_transport_display().lower()})" if c.motif_transport else "")))
        if c.commentaire_commission:
            lignes.append(("Commentaires", c.commentaire_commission))
        lignes.append(("Cadre", _nom(c.decide_par)))
        el += _rubrique("Décision de la commission", lignes, st)
    else:
        el += _rubrique("Décision de la commission (réservé au pôle insertion)", [
            f"{_case()}Validé pour …… mois, du …/…/…… au …/…/……   {_case()}Validé sauf action : ………………………………",
            f"{_case()}Ajourné   {_case()}Non validé, le …/…/…… – motif : ……………………………………………………",
            f"Aide aux transports : {_case()}oui  {_case()}non – motif : {_case()}dérogation  "
            f"{_case()}durée maximale déjà accordée  {_case()}conditions non remplies",
        ], st)
    # Engagements et signatures
    el += _rubrique("Engagements", [
        _case(c.engagement_renouvellement) + "Je m'engage à préparer le renouvellement de mon contrat avec mon référent un mois avant son échéance.",
        _case(c.accord_allocataire) + "J'ai pris connaissance du contenu de ce contrat et j'en accepte "
        "les engagements.",
    ], st)
    sig = Table([[Paragraph("<b>Le bénéficiaire</b>", st["Normal"]), Paragraph("<b>Le référent</b>", st["Normal"])],
                 [Paragraph(f"Signé le {_d(c.date_signature)}", st["Normal"]),
                  Paragraph(f"{_t(_nom(c.referent))}, le {_d(c.date_signature)}", st["Normal"])],
                 ["\n\n\n", ""]], colWidths=[8.7 * cm, 8.7 * cm])
    sig.setStyle(TableStyle([('BOX', (0, 0), (0, -1), 0.5, BORD), ('BOX', (1, 0), (1, -1), 0.5, BORD)]))
    el.append(KeepTogether([sig]))
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------- courriers
def _valeurs_communes(c):
    b, p = c.beneficiaire, ParametresRSA.courant()
    return {"civilite_appel": "Monsieur" if b.civilite == 'M.' else "Madame",
            "beneficiaire": f"{b.prenom} {b.nom.upper()}", "date_naissance": _d(b.date_naissance),
            "nom_contrat": p.nom_contrat.lower() if p.nom_contrat[:1].isupper() and p.nom_contrat[1:2].islower()
            else p.nom_contrat,
            "numero_contrat": c.numero, "pole": c.pole.nom if c.pole else "", "referent": _nom(c.referent),
            "mds": c.mds.nom if c.mds else ""}


def _courrier(c, code, valeurs, conditions, expediteur_lignes, destinataire_lignes, date_lettre, titre):
    from core.courriers import modele_texte, rendu
    buffer = BytesIO()
    doc = _doc(buffer, titre)
    st = get_ditas_styles()
    m = modele_texte(code)   # textes modifiables en administration (Modèles de courriers)
    el = [Paragraph(expediteur_lignes, st["Normal"]), Spacer(1, 0.5 * cm)]
    if destinataire_lignes:
        el += [Table([["", Paragraph(destinataire_lignes, st["Normal"])]], colWidths=[9 * cm, 8 * cm]),
               Spacer(1, 0.8 * cm)]
    ville = c.mds.ville if c.mds else ""
    el += [Paragraph(f"{escape(ville)}, le {_d(date_lettre)}", st["Normal"]), Spacer(1, 0.4 * cm),
           Paragraph(f"<b>Objet :</b> {rendu.ligne(m['objet'], valeurs, conditions)}", st["Normal"]),
           Spacer(1, 0.5 * cm)]
    for para in rendu.paragraphes(m["corps"], valeurs, conditions):
        el += [Paragraph(para, st["Normal"]), Spacer(1, 0.3 * cm)]
    el += [Spacer(1, 0.6 * cm),
           Table([["", Paragraph(rendu.bloc(m["signature"], valeurs, conditions), st["Normal"])]],
                 colWidths=[9 * cm, 8 * cm])]
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer


def _bloc_mds(c):
    m = c.mds
    if not m:
        return ""
    return (f"<b>{escape(m.nom)}</b><br/>{_t(m.adresse)}<br/>{escape(m.code_postal)} {escape(m.ville)}"
            + (f"<br/>Tél. {escape(m.telephone)}" if m.telephone else ""))


def courrier_medecin_pdf(c):
    """Demande de certificat, remise au bénéficiaire pour son médecin traitant (aucun contenu médical)."""
    from django.utils import timezone
    pole = c.pole
    adresse = (f"Médecin du {pole.nom}, {pole.adresse}, {pole.code_postal} {pole.ville}".replace(" ,", ",")
               if pole else "Médecin du pôle insertion")
    valeurs = {**_valeurs_communes(c), "adresse_pli": adresse,
               "adresse_mssante": pole.email_mssante_medecin if pole else ""}
    conditions = {"si_mssante": bool(pole and pole.email_mssante_medecin)}
    return _courrier(c, "RSA_CERTIFICAT_MEDECIN", valeurs, conditions, _bloc_mds(c), "",
                     c.certificat_demande_le or timezone.localdate(), f"Certificat médical {c.numero}")


def notification_pdf(c):
    from datetime import timedelta
    b = c.beneficiaire
    C = ContratInsertion
    non_retenues = "; ".join(f"{l.intitule} ({l.motif_non_retenue})" for l in c.lignes.filter(non_retenue=True))
    valeurs = {**_valeurs_communes(c), "date_decision": _d(c.date_decision), "date_debut": _d(c.date_debut),
               "date_fin": _d(c.date_fin), "duree_mois": c.duree_validee_mois or "",
               "actions_non_retenues": non_retenues, "motif": c.motif_decision,
               "date_renouvellement": _d(c.date_fin - timedelta(days=ParametresRSA.courant().delai_alerte_jours))
               if c.date_fin else "",
               "signataire": _nom(c.decide_par)}
    conditions = {"si_valide": c.decision in (C.VALIDE, C.VALIDE_SAUF_ACTION),
                  "si_sauf_action": c.decision == C.VALIDE_SAUF_ACTION, "si_ajourne": c.decision == C.AJOURNE,
                  "si_non_valide": c.decision == C.NON_VALIDE, "si_transport_accorde": c.decision_transport == 'OUI',
                  "si_transport_refuse": c.decision_transport == 'NON'}
    pole = c.pole
    expediteur = (f"<b>{escape(pole.nom)}</b><br/>{_t(pole.adresse)}<br/>{escape(pole.code_postal)} {escape(pole.ville)}"
                  if pole else _bloc_mds(c))
    dest = (f"{escape(b.get_civilite_display())} {escape(b.prenom)} {escape(b.nom.upper())}<br/>{_t(b.adresse)}<br/>"
            f"{escape(b.code_postal)} {escape(b.ville)}")
    return _courrier(c, "RSA_NOTIFICATION_DECISION", valeurs, conditions, expediteur, dest, c.date_decision,
                     f"Notification {c.numero}")
