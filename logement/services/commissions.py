# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/commissions.py
"""Commissions de la prévention des expulsions (CAPEX locale, commission préfectorale, CCAPEX) : séances, ordre du
jour, actualisation de la situation par la MDS (préremplie, visée par le cadre, transmise), avis de la commission.

L'ordre du jour ne contient que ce qui sert à la séance (dossier, ménage, MDS, étape, dette, état de
l'actualisation) : jamais de données de santé ni de détail de l'évaluation sociale."""
import io
from decimal import Decimal
from xml.sax.saxutils import escape

from django.utils import timezone

from logement.models import CommissionExpulsion as K, PassageCommission as P

from . import expulsion as X
from .expulsion import _message, prevenir_sl

T, L, R = 'texte', 'long', 'choix'


def _c(cle, label, type_=T, options=None, largeur=1):
    return {'cle': cle, 'label': label, 'type': type_, 'options': options or [], 'largeur': largeur}


SECTIONS = [
    ("Rencontres avec la famille", [
        _c('dates_rencontres', "Dates des rencontres", largeur=2), _c('vad', "Visites à domicile", R, ["oui", "non"]),
        _c('presente', "La famille s'est présentée", R, ["oui", "non"]),
        _c('accompagnant', "Accompagnant social (nom et fonction)", largeur=2)]),
    ("Ménage et bailleur", [
        _c('adresse', "Adresse", largeur=2), _c('num_caf', "N° CAF"),
        _c('bailleur_type', "Bailleur", R, ["privé", "public"]),
        _c('parent1', "Parent 1 (nom, prénom, date de naissance)", largeur=2),
        _c('parent2', "Parent 2 (nom, prénom, date de naissance)", largeur=2),
        _c('enfants', "Enfants (un par ligne : prénom, nom, date de naissance)", L, largeur=3),
        _c('revenus', "Revenus de la famille (un par ligne : nature – montant)", L, largeur=3),
        _c('total_revenus', "Total des revenus (€)")]),
    ("Logement actuel", [
        _c('type_logement', "Type de logement"), _c('adapte', "Adapté à la composition familiale", R, ["oui", "non"]),
        _c('loyer_hc', "Loyer hors charges (€)"), _c('charges', "Charges (€)"),
        _c('loyer_cc', "Loyer charges comprises (€)"), _c('aide_logement', "Aide au logement (€)"),
        _c('loyer_residuel', "Loyer résiduel (€)"), _c('regul_charges', "Régularisation de charges (€)")]),
    ("Dette bailleur", [
        _c('dette_nature', "Nature de la dette", largeur=2), _c('dette_montant', "Montant total (€)"),
        _c('mois_loyer', "Nombre de mois de loyer HC"), _c('montant_loyer', "Montant (€)"),
        _c('mois_charges', "Nombre de mois de charges"), _c('montant_charges', "Montant (€)"),
        _c('historique_dette', "Historique de la dette", L, largeur=3),
        _c('mesures', "Mesures déjà mises en place (FSL, concordat, échéancier…), montants et dates", L, largeur=3)]),
    ("Évaluation et propositions", [
        _c('evaluation', "Évaluation sociale", L, largeur=3), _c('propositions', "Propositions", L, largeur=3)]),
]
CHAMPS = {c['cle']: c for _, cs in SECTIONS for c in cs}


# ------------------------------------------------------------------------------------------------- droits
def commissions_visibles(user):
    qs = K.objects.prefetch_related('mds')
    if X.est_sl(user) or X.est_admin(user) or user.a_la_capacite('expulsion_sl_stats'):
        return qs
    mes = X.mds_de(user)
    return (qs.filter(mds__in=mes) | qs.filter(mds__isnull=True)).distinct()


def peut_gerer(user, commission=None):
    """Créer une séance, saisir les avis : le Service Logement, ou le cadre d'une MDS concernée."""
    if X.est_sl(user) or X.est_admin(user):
        return True
    if not user.a_la_capacite('peut_valider'):
        return False
    if commission is None:
        return X.mds_de(user).exists()
    return commission.mds.filter(pk__in=X.mds_de(user)).exists()


def peut_viser(user, passage):
    d = passage.dossier
    return bool(d.mds_id and user.a_la_capacite('peut_valider') and user.a_acces_mds(d.mds))


# ------------------------------------------------------------------------------------------------- actualisation
def _date(x):
    return x.strftime('%d/%m/%Y') if x else ""


def _m(v):
    from .dsf import montant
    return montant(v)


def preremplir(passage, user):
    from mds.fonctions import fonction_de
    from logement.models import ConvocationExpulsion as C, DemandeFSL
    d, b = passage.dossier, passage.dossier.beneficiaire
    v = {'adresse': d.adresse_complete, 'num_caf': d.numero_allocataire,
         'bailleur_type': "public" if d.type_bailleur == 'SOCIAL' else ("privé" if d.type_bailleur else ""),
         'loyer_hc': _m(d.loyer), 'charges': _m(d.charges), 'loyer_cc': _m(d.loyer_total),
         'dette_montant': _m(d.dette), 'dette_nature': "Loyers et charges impayés" if d.dette else ""}
    ref = d.referent or user
    f = fonction_de(ref, d.mds)
    v['accompagnant'] = (ref.get_full_name() or ref.username) + (f", {f}" if f else "")
    venus = d.convocations.filter(statut=C.VENU).order_by('date_rdv')
    if venus:
        v['dates_rencontres'] = ", ".join(_date(timezone.localtime(c.date_rdv)) for c in venus)
        v['presente'] = "oui"
    elif d.convocations.filter(statut=C.ABSENT).exists():
        v['presente'] = "non"
    v['historique_dette'] = "\n".join(f"{e.date:%d/%m/%Y} – {e.get_type_etape_display()}"
                                      + (f" : {e.commentaire}" if e.commentaire else "")
                                      for e in d.etapes.order_by('date', 'pk'))
    dsf = d.diagnostics.filter(type_document='DSF').order_by('-cree_le').first()
    if dsf and (dsf.donnees or {}).get('Evaluation sociale'):
        v['evaluation'] = f"(Reprise du diagnostic social et financier, à actualiser.)\n{dsf.donnees['Evaluation sociale']}"
    if b:
        _famille(b, v)
        _revenus(b, v)
        mesures = [f"FSL {x.get_type_aide_display().lower()} – {x.get_statut_display().lower()}"
                   + (f", envoyé le {x.date_envoi:%d/%m/%Y}" if getattr(x, 'date_envoi', None) else "")
                   for x in DemandeFSL.objects.filter(beneficiaire=b).order_by('-pk')[:3]]
        plans = [f"{e.date:%d/%m/%Y} – plan d'apurement" + (f" : {e.commentaire}" if e.commentaire else "")
                 for e in d.etapes.filter(type_etape='PLAN_APUREMENT')]
        if mesures or plans:
            v['mesures'] = "\n".join(mesures + plans)
    try:
        if d.loyer_total and v.get('aide_logement'):
            v['loyer_residuel'] = _m(Decimal(str(d.loyer_total)) - Decimal(v['aide_logement'].replace(',', '.')))
    except Exception:       # noqa: BLE001
        pass
    return {k: x for k, x in v.items() if x not in (None, "")}


def _famille(b, v):
    from .fsl import composition
    comp = composition(b)
    parents = [p for p in comp if p['role'] in ('DEMANDEUR', 'CONJOINT')]
    for i, p in enumerate(parents[:2], 1):
        v[f'parent{i}'] = f"{p['nom'].upper()} {p['prenom']}" + (f", né(e) le {p['date_naissance']}" if p.get('date_naissance') else "")
    enfants = [p for p in comp if p['role'] == 'ENFANT']
    if enfants:
        v['enfants'] = "\n".join(f"{p['prenom']} {p['nom'].upper()}" + (f", {p['date_naissance']}" if p.get('date_naissance') else "")
                                 for p in enfants)


def _revenus(b, v):
    from AidFi.services.budget_afase import RESSOURCES
    from beneficiaire.budget import budget_en_cours
    from .dsf import d as dec
    budget = budget_en_cours(b)
    if not budget:
        return
    lignes = (budget.ressources or {}).get('lignes', {})
    libelles = {code: lib for _, ls in RESSOURCES for code, lib in ls}
    out, total = [], Decimal(0)
    for code, val in lignes.items():
        m = sum((dec(val.get(c)) for c in ('demandeur', 'conjoint', 'autres')), Decimal(0))
        if m:
            if code == 'logement':
                v['aide_logement'] = _m(m)
                continue
            out.append(f"{libelles.get(code, code).split(' (')[0]} – {_m(m)} €")
            total += m
    if out:
        v['revenus'] = "\n".join(out)
        v['total_revenus'] = _m(total)


# ------------------------------------------------------------------------------------------------- circuit
def inscrire(commission, dossier, user):
    p, cree = P.objects.get_or_create(commission=commission, dossier=dossier, defaults={'redacteur': None})
    if cree:
        p.actualisation = preremplir(p, dossier.referent or user)
        p.tracer(user, "Inscrit à l'ordre du jour", str(commission))
        p.save()
        dossier.tracer(user, "Inscrit à une commission", str(commission))
        dossier.save()
        if dossier.referent_id and dossier.referent_id != user.pk:
            _message(user, dossier.referent, dossier, f"Commission : {dossier.nom_complet} – {commission}",
                     f"Le dossier {dossier.numero} est inscrit à la séance « {commission} ». "
                     + (f"Actualisation attendue le {commission.date_limite:%d/%m/%Y}. " if commission.date_limite else "")
                     + "Elle est préremplie dans CID.")
    return p, cree


def demander_visa(p, user):
    from beneficiaire.transfert import responsable_mds
    p.statut, p.redacteur = P.A_VISER, user
    p.tracer(user, "Visa du cadre demandé")
    p.save()
    cadre = responsable_mds(p.dossier.mds)
    _message(user, cadre, p.dossier, f"Visa demandé : actualisation pour {p.commission} – {p.dossier.nom_complet}",
             f"{user.get_full_name() or user.username} demande votre visa sur l'actualisation du dossier "
             f"{p.dossier.numero} pour la séance « {p.commission} ».")
    return cadre


def viser(p, user):
    p.statut, p.cadre, p.date_validation_cadre = P.VISEE, user, timezone.now()
    p.tracer(user, "Visée par le cadre")
    p.save()


def marquer_transmis(p, user, mode):
    p.statut, p.date_envoi = P.TRANSMISE, timezone.localdate()
    p.tracer(user, "Transmise" + (" par mail" if mode == 'MAIL' else " (imprimée)"))
    p.save()


def saisir_avis(p, user, avis, detail):
    from logement.models import EtapeExpulsion
    p.avis, p.avis_detail = avis, detail
    p.tracer(user, "Avis de la commission", p.get_avis_display())
    p.save()
    type_etape = 'CAPEX_LOCALE' if p.commission.type_commission == K.LOCALE else 'COMMISSION_PREFECTORALE'
    EtapeExpulsion.objects.update_or_create(
        dossier=p.dossier, type_etape=type_etape, date=p.commission.date,
        defaults={'commentaire': f"{p.get_avis_display()}" + (f" – {detail}" if detail else ""), 'saisi_par': user})
    d = p.dossier
    d.tracer(user, "Avis de la commission", f"{p.commission} : {p.get_avis_display()}")
    d.save()
    for dest in {x for x in (d.referent,) if x}:
        _message(user, dest, d, f"Avis : {p.commission} – {d.nom_complet}",
                 f"Avis rendu pour le dossier {d.numero} : {p.get_avis_display()}." + (f"\n{detail}" if detail else ""))
    if not X.est_sl(user):
        prevenir_sl(d, user, f"Avis : {p.commission} – {d.nom_complet}",
                    f"Avis rendu pour le dossier {d.numero} : {p.get_avis_display()}.")


# ------------------------------------------------------------------------------------------------- PDF
def _st():
    from AidFi.services.afase_pdf import get_ditas_styles
    return get_ditas_styles()


def _construire(elements, titre, paysage=False):
    from AidFi.services.afase_pdf import draw_page_template
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4) if paysage else A4, topMargin=3.5 * cm, bottomMargin=2 * cm,
                            leftMargin=1.5 * cm, rightMargin=1.5 * cm, title=titre, author="CID")
    doc.build(elements, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    return buf.getvalue()


def _t(x):
    return escape(str(x or "")).replace("\n", "<br/>")


def actualisation_pdf(p):
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from .placements_fsl import visa
    st, v, d = _st(), p.actualisation or {}, p.dossier
    mds = d.mds
    P_ = lambda x: Paragraph(x, st["Normal"])          # noqa: E731

    def tab(lignes, largeurs):
        t = Table([[P_(c) for c in l] for l in lignes], colWidths=largeurs)
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('FONTSIZE', (0, 0), (-1, -1), 8)]))
        return t
    el = [Paragraph("DISPOSITIF DE PRÉVENTION DES EXPULSIONS DOMICILIAIRES<br/>ACTUALISATION POUR "
                    + _t(p.commission.get_type_commission_display().upper()), st["TitreOfficiel"]),
          P_(f"<b>Séance :</b> {_t(p.commission)} – <b>Dossier :</b> {_t(d.numero)}"
             + (f" – <b>EXPLOC :</b> {_t(d.numero_exploc)}" if d.numero_exploc else "")), Spacer(1, 6)]
    for titre, champs in SECTIONS:
        lignes = []
        for c in champs:
            if c['cle'] in v:
                lignes.append([f"<b>{_t(c['label'])}</b>", _t(v[c['cle']])])
        if titre == "Ménage et bailleur":
            lignes.insert(0, ["<b>Ménage</b>", _t(d.nom_complet)])
        if titre == "Rencontres avec la famille" and mds:
            lignes.append(["<b>MDS</b>", _t(f"{mds.nom} – {mds.adresse} {mds.code_postal} {mds.ville}"
                                             + (f" – {mds.telephone}" if mds.telephone else "")
                                             + (f" – {mds.email}" if mds.email else ""))])
        if lignes:
            el += [Paragraph(titre.upper(), st["SectionHeader"]), tab(lignes, [6 * cm, 12 * cm]), Spacer(1, 4)]
    texte, image = visa(p)
    el += [Spacer(1, 10), P_(f"<b>{_t(texte)}</b>" if texte else "<i>Non visée.</i>")]
    if image:
        from reportlab.platypus import Image
        try:
            el.append(Image(io.BytesIO(image['image']), width=4 * cm, height=1.2 * cm, kind='proportional'))
        except Exception:    # noqa: BLE001
            pass
    return _construire(el, f"Actualisation {d.numero}")


def odj_pdf(commission, user):
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    st = _st()
    P_ = lambda x: Paragraph(x, st["Normal"])          # noqa: E731
    lignes = [["<b>N°</b>", "<b>Dossier</b>", "<b>Ménage, commune</b>", "<b>MDS, référent</b>", "<b>Étape</b>",
               "<b>Dette</b>", "<b>Actualisation</b>", "<b>Avis</b>"]]
    visibles = X.dossiers_visibles(user)
    for i, p in enumerate(commission.passages.filter(dossier__in=visibles).select_related('dossier__mds', 'dossier__referent'), 1):
        d = p.dossier
        e = d.etape_courante
        lignes.append([str(i), _t(d.numero), _t(f"{d.nom_complet}<br/>{d.ville}"),
                       _t(f"{d.mds.nom if d.mds else '—'}<br/>{d.referent.get_full_name() if d.referent else ''}"),
                       _t(e.get_type_etape_display() if e else "—"), _t(f"{_m(d.dette)} €" if d.dette else "—"),
                       _t(p.get_statut_display()), _t(p.get_avis_display() if p.avis else "")])
    t = Table([[P_(c) for c in l] for l in lignes],
              colWidths=[0.8 * cm, 3 * cm, 5 * cm, 4.5 * cm, 4 * cm, 2.3 * cm, 3.5 * cm, 3.5 * cm], repeatRows=1)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb'))]))
    el = [Paragraph(f"ORDRE DU JOUR – {_t(commission.nom.upper())}", st["TitreOfficiel"]),
          P_(f"<b>{_t(commission.get_type_commission_display())}</b> du {commission.date:%d/%m/%Y}"
             + (f" à {_t(commission.heure)}" if commission.heure else "") + (f" – {_t(commission.lieu)}" if commission.lieu else "")),
          Spacer(1, 6), t, Spacer(1, 6),
          P_("<i>Document à usage interne de la commission. Ne pas diffuser.</i>")]
    return _construire(el, f"Ordre du jour {commission}", paysage=True)
