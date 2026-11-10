# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/hebergement_pdf.py
"""PDF des fiches d'hébergement d'urgence (demande, renouvellement, rapport final, orientation vers l'État) :
dactylographiées, avec le visa du cadre (initiales et date). Le courriel imprimé est celui de la MDS, jamais
l'adresse nominative d'un agent."""
import io
from xml.sax.saxutils import escape

from logement.models import FicheHebergement as F

from . import hebergement as H

TITRES = {F.SAS: "FICHE DE LIAISON – DEMANDE D'HÉBERGEMENT D'URGENCE",
          F.RENOUVELLEMENT: "HÉBERGEMENT D'URGENCE – RAPPORT DE PRISE EN CHARGE<br/>RENOUVELLEMENT",
          F.FINAL: "HÉBERGEMENT D'URGENCE – RAPPORT DE PRISE EN CHARGE<br/>RAPPORT FINAL",
          F.ETAT: "FICHE D'ORIENTATION VERS LES SERVICES DE L'ÉTAT (DDETS)"}


def _t(x):
    return escape(str(x or "")).replace("\n", "<br/>")


def _agent(user, mds):
    from mds.fonctions import fonction_de
    from .fsl import coordonnees_ts
    if not user:
        return ""
    c = coordonnees_ts(user, mds)
    f = fonction_de(user, mds)
    return (user.get_full_name() or user.username) + (f"<br/>{_t(f)}" if f else "") + (f"<br/>{_t(c['telephone'])}" if c['telephone'] else "")


def fiche_pdf(f):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import CondPageBreak, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles
    from beneficiaire.transfert import responsable_mds
    from .placements_fsl import visa
    st, v, d = get_ditas_styles(), f.donnees or {}, f.dossier
    mds = d.mds
    P = lambda x: Paragraph(x, st["Normal"])          # noqa: E731
    gris = colors.HexColor('#e5e7eb')

    def tab(lignes, largeurs, entete=False):
        t = Table([[P(c) for c in l] for l in lignes], colWidths=largeurs, repeatRows=1 if entete else 0)
        style = [('GRID', (0, 0), (-1, -1), 0.4, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP')]
        if entete:
            style.append(('BACKGROUND', (0, 0), (-1, 0), gris))
        t.setStyle(TableStyle(style))
        return t

    def section(titre, bloc):
        return [KeepTogether([Paragraph(titre.upper(), st["SectionHeader"]), bloc]), Spacer(1, 4)]

    redacteur = f.redacteur or d.referent
    cadre = f.cadre or responsable_mds(mds)
    date_fiche = f.date_validation_cadre or f.cree_le
    el = [Paragraph(TITRES[f.type_fiche], st["TitreOfficiel"]),
          P(f"<b>Date de la demande :</b> {date_fiche:%d/%m/%Y} – <b>Dossier :</b> {_t(d.numero)}"),
          P(f"<b>Maison départementale de la solidarité :</b> {_t(mds.nom)}"
            + (f" – {_t(mds.telephone)}" if mds.telephone else "") + (f" – {_t(mds.email)}" if mds.email else "")),
          Spacer(1, 6)]
    qui = [["<b>Référent social chargé du suivi de la famille</b>", "<b>Travailleur social qui instruit la fiche</b>",
            "<b>Cadre de la MDS</b>"],
           [_agent(d.referent, mds), _agent(redacteur, mds) if redacteur and redacteur != d.referent else "—",
            _agent(cadre, mds)]]
    el += [tab(qui, [6 * cm] * 3, entete=True), Spacer(1, 6)]

    pers = [["<b>Qualité</b>", "<b>Autorité parentale</b>", "<b>Nom</b>", "<b>Prénom</b>", "<b>Date de naissance</b>",
             "<b>Lieu de naissance</b>"]]
    pers += [[_t(p.get(c)) for c in H.COLONNES_PERSONNE] for p in v.get('personnes') or []]
    el += section("Personnes concernées par l'hébergement",
                  tab(pers, [2.2 * cm, 2.3 * cm, 4 * cm, 3.5 * cm, 2.7 * cm, 3.3 * cm], entete=True))

    rev = [[f"{_t(lib)}" + (f" ({_t(v[f'rev_{c}_detail'])})" if v.get(f"rev_{c}_detail") else ""), _t(v[f"rev_{c}"]) + " €"]
           for c, lib in H.REVENUS if v.get(f"rev_{c}")]
    bloc_revenus = section("Revenus", tab([["<b>Nature</b>", "<b>Montant mensuel</b>"]] + (rev or [["Aucune ressource déclarée", ""]]),
                                          [13 * cm, 5 * cm], entete=True))

    def rubriques(champs):
        return [[f"<b>{_t(c['label'])}</b>", _t(v[c['cle']])] for c in champs if v.get(c['cle'])]

    sections = H.SECTIONS[f.type_fiche]
    titre0, champs0 = sections[0]
    lignes0 = rubriques(champs0)
    if lignes0:
        el += section(titre0, tab(lignes0, [6.5 * cm, 11.5 * cm]))
    el += bloc_revenus
    for titre, champs in sections[1:]:
        for c in champs:                               # un pavé par rubrique : les textes longs passent d'une page à l'autre
            if v.get(c['cle']):
                el += [CondPageBreak(3 * cm), Paragraph(_t(c['label']).upper(), st["SectionHeader"]), P(_t(v[c['cle']])),
                       Spacer(1, 4)]

    if f.type_fiche in (F.SAS, F.ETAT):
        dem = [["<b>Démarche</b>", "<b>Date</b>", "<b>Réponse, proposition</b>"]]
        dem += [[_t(m.get_type_demarche_display() + (f" – {m.precision}" if m.precision else "")), f"{m.date:%d/%m/%Y}",
                 _t(m.reponse)] for m in d.demarches.all()]
        if len(dem) == 1:
            dem.append(["Aucune démarche tracée", "", ""])
        el += section("Démarches d'hébergement", tab(dem, [7 * cm, 2.5 * cm, 8.5 * cm], entete=True))

    texte, image = visa(f)
    bas = [P(f"<b>Travailleur social instructeur :</b> {_t(redacteur.get_full_name() if redacteur else '')}"),
           P(f"<b>{_t(texte)}</b> – {_t(cadre.get_full_name() if f.cadre else '')}" if texte
             else "<i>Fiche non visée par le cadre : elle ne peut pas être transmise.</i>")]
    if image:
        try:
            bas.append(Image(io.BytesIO(image['image']), width=4 * cm, height=1.2 * cm, kind='proportional'))
        except Exception:    # noqa: BLE001
            pass
    el += [Spacer(1, 10), KeepTogether(bas)]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=3.5 * cm, bottomMargin=2 * cm, leftMargin=1.5 * cm,
                            rightMargin=1.5 * cm, title=f"{f.get_type_fiche_display()} {d.numero}", author="CID")
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    return buf.getvalue()
