# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/asell.py
"""Orientation ASELL : rubriques des fiches (généraliste, renforcée), préremplissage depuis l'usager, son budget, ses
demandes FSL et, pour l'ASELL renforcé, son dossier de prévention des expulsions ; PDF.

La fiche porte la signature du travailleur social (pas de visa du cadre sur le modèle). Le courriel imprimé est celui
de la MDS, jamais l'adresse nominative d'un agent."""
import io
from decimal import Decimal
from xml.sax.saxutils import escape

from django.utils import timezone

from logement.models import OrientationASELL as A

T, L, R, X = 'texte', 'long', 'choix', 'multi'
ON = ["oui", "non"]


def _c(cle, label, type_=T, options=None, largeur=1):
    return {'cle': cle, 'label': label, 'type': type_, 'options': options or [], 'largeur': largeur}


_BENEFICIAIRE = ("Bénéficiaire", [
    _c('nom_prenom', "Nom et prénom", largeur=2), _c('num_caf', "N° CAF ou MSA"),
    _c('adresse', "Adresse", largeur=2), _c('telephone', "Téléphone"),
    _c('composition', "Composition familiale", R, ["Personne isolée", "Couple", "Famille monoparentale",
                                                    "Couple avec enfants"]),
    _c('nb_enfants', "Nombre d'enfants à charge"), _c('autre_personne', "Autre personne à charge")])


def _budget(renforce):
    champs = [_c('ressources', "Ressources mensuelles : nature et montant, hors AL et APL (une par ligne)", L, largeur=3),
              _c('aide_logement', "Montant de l'AL ou de l'APL (€)"),
              _c('loyer', "Loyer mensuel ou participation à l'hébergement (€)"),
              _c('dettes', "Crédits et dettes", R, ON), _c('dettes_detail', "Nature et montant des crédits et dettes", largeur=3),
              _c('fsl_en_cours', "FSL en cours", R, ON), _c('surendettement', "Dossier de surendettement", R, ON)]
    if renforce:
        champs.append(_c('surendettement_constitue', "Dossier de surendettement constitué", R, ON))
    return ("Budget", champs)


SECTIONS = {
    A.GENERALISTE: [
        _BENEFICIAIRE, _budget(False),
        ("Logement", [
            _c('statut_logement', "Situation", R, ["Parc public", "Parc privé", "Propriétaire occupant", "Hébergement",
                                                   "Sans résidence stable", "Autre"]),
            _c('bailleur', "Bailleur (parc public) ou précision"), _c('typologie', "Typologie (T1, T2…)"),
            _c('motifs', "Éléments motivant l'orientation", X,
               ["Logement inadapté", "Logement non décent", "Congé pour vente", "Endettement locatif, accession aux charges",
                "Absence de logement", "Commandement de payer", "Autre"], largeur=3),
            _c('dette_montant', "Montant de l'endettement (€)"), _c('commandement_date', "Date du commandement de payer"),
            _c('motif_autre', "Autre motif"),
            _c('asell_deja', "Ménage ayant déjà bénéficié d'une mesure ASELL", R, ON), _c('asell_date', "Date de la mesure")]),
        ("Évaluation du travailleur social", [_c('evaluation', "Évaluation", L, largeur=3), _c('fait_a', "Fait à")]),
    ],
    A.RENFORCE: [
        _BENEFICIAIRE, _budget(True),
        ("Logement et procédure d'expulsion", [
            _c('statut_logement', "Situation", R, ["Parc public", "Parc privé"]),
            _c('bailleur', "Bailleur (parc public)"), _c('typologie', "Typologie (T1, T2…)"),
            _c('assignation_date', "Assignation le"), _c('commandement_quitter_date', "Commandement de quitter les lieux le"),
            _c('cfp_demande_date', "Concours de la force publique demandé le"), _c('cfp_accorde_date', "Concours accordé le"),
            _c('motifs', "Motif de la procédure d'expulsion", X,
               ["Dette locative", "Défaut d'assurance", "Vente", "Trouble de voisinage", "Autre"], largeur=3),
            _c('dette_montant', "Montant de la dette locative (€)"), _c('motif_autre', "Autre motif", largeur=2),
            _c('expulsion_deja', "Ménage ayant déjà connu une expulsion", R, ON), _c('expulsion_date', "Date"),
            _c('asell_deja', "Ménage ayant déjà bénéficié d'une mesure ASELL", R, ON), _c('asell_date', "Date de la mesure"),
            _c('fsl_deja', "Ménage ayant déjà bénéficié d'un FSL", R, ON), _c('fsl_date', "Date du FSL")]),
        ("Évaluation du travailleur social", [_c('evaluation', "Évaluation", L, largeur=3), _c('fait_a', "Fait à")]),
    ],
}
CHAMPS = {t: {c['cle']: c for _, cs in s for c in cs} for t, s in SECTIONS.items()}


# ------------------------------------------------------------------------------------------------- droits
def peut_voir(user, a):
    return a.beneficiaire.niveau_acces(user) == 'complet'


def peut_ecrire(user, a):
    from beneficiaire.views import user_peut_agir_sur_beneficiaire
    return peut_voir(user, a) and user_peut_agir_sur_beneficiaire(user, a.beneficiaire)


# ------------------------------------------------------------------------------------------------- préremplissage
def _d(x):
    return x.strftime('%d/%m/%Y') if x else ""


def _m(v):
    from .hebergement import _montant
    return _montant(v)


def _budget_usager(b, v):
    from AidFi.services.budget_afase import RESSOURCES
    from beneficiaire.budget import budget_en_cours
    from .dsf import d as dec
    budget = budget_en_cours(b)
    if not budget:
        return
    libelles = {code: lib.split(' (')[0] for _, ls in RESSOURCES for code, lib in ls}
    lignes = []
    for code, val in ((budget.ressources or {}).get('lignes', {})).items():
        m = sum((dec(val.get(c)) for c in ('demandeur', 'conjoint', 'autres')), Decimal(0))
        if not m:
            continue
        if code == 'logement':
            v['aide_logement'] = _m(m)
        else:
            lignes.append(f"{libelles.get(code, code)} : {_m(m)} €")
    if lignes:
        v['ressources'] = "\n".join(lignes)
    loyer = ((budget.charges or {}).get('lignes', {})).get('loyer') or {}
    m = sum((dec(loyer.get(c)) for c in ('payee', 'non_payee')), Decimal(0))
    if m:
        v['loyer'] = _m(m)
    dettes = [x for x in (budget.dettes or []) if isinstance(x, dict) and (x.get('creancier') or x.get('montant'))]
    if dettes:
        v['dettes'] = "oui"
        v['dettes_detail'] = " ; ".join(f"{x.get('creancier') or 'dette'} : {x.get('montant') or '?'} €" for x in dettes)[:400]


def preremplir(a, user):
    from logement.models import DemandeFSL
    from .hebergement import menage
    b = a.beneficiaire
    v = {'nom_prenom': f"{b.nom.upper()} {b.prenom}", 'num_caf': b.numero_caf or "",
         'adresse': " ".join(x for x in (b.adresse.replace("\n", " "), b.code_postal, b.ville) if x),
         'telephone': b.telephone_mobile or b.telephone_fixe or "", 'fait_a': a.mds.ville or ""}
    m = menage(b)
    couple = any(x['role'] == 'CONJOINT' for x in m)
    enfants = sum(1 for x in m if x['role'] == 'ENFANT')
    v['composition'] = ("Couple avec enfants" if couple and enfants else "Couple" if couple
                        else "Famille monoparentale" if enfants else "Personne isolée")
    if enfants:
        v['nb_enfants'] = str(enfants)
    _budget_usager(b, v)
    fsl = DemandeFSL.objects.filter(beneficiaire=b)
    en_cours = fsl.exclude(statut__in=(DemandeFSL.ACCORDEE, DemandeFSL.REFUSEE, DemandeFSL.ABANDONNEE)).exists()
    v['fsl_en_cours'] = "oui" if en_cours else "non"
    precedente = (A.objects.filter(beneficiaire=b, statut=A.ENVOYEE).exclude(pk=a.pk).order_by('-date_envoi').first())
    v['asell_deja'] = "oui" if precedente else "non"
    if precedente:
        v['asell_date'] = _d(precedente.date_envoi)
    dl = getattr(b, 'demande_logement', None)
    if dl and dl.typologie_souhaitee and a.volet == A.ACCES:
        v['typologie'] = dl.typologie_souhaitee
    d = a.dossier_expulsion
    if d:
        v['statut_logement'] = "Parc public" if d.type_bailleur == 'SOCIAL' else ("Parc privé" if d.type_bailleur else "")
        if d.type_bailleur == 'SOCIAL':
            v['bailleur'] = (d.proprietaire or "").split("\n")[0][:100]
        if d.dette:
            v['dette_montant'] = _m(d.dette)
            v.setdefault('dettes', "oui")
        if d.loyer_total and 'loyer' not in v:
            v['loyer'] = _m(d.loyer_total)
        etapes = {e.type_etape: e.date for e in d.etapes.order_by('date', 'pk')}
        if a.type_mesure == A.RENFORCE:
            v['motifs'] = ["Dette locative"] if d.dette else []
            for cle, code in (('assignation_date', 'ASSIGNATION'), ('commandement_quitter_date', 'COMMANDEMENT_QUITTER'),
                              ('cfp_demande_date', 'DEMANDE_CFP'), ('cfp_accorde_date', 'CFP_ACCORDE')):
                v[cle] = _d(etapes.get(code))
            accorde = fsl.filter(statut=DemandeFSL.ACCORDEE).order_by('-date_decision').first()
            v['fsl_deja'] = "oui" if accorde else "non"
            if accorde:
                v['fsl_date'] = _d(accorde.date_decision)
        else:
            v['motifs'] = (["Endettement locatif, accession aux charges"] if d.dette else []) \
                + (["Commandement de payer"] if 'COMMANDEMENT_PAYER' in etapes else [])
            v['commandement_date'] = _d(etapes.get('COMMANDEMENT_PAYER'))
    return {k: x for k, x in v.items() if x not in (None, "", [])}


def lire_formulaire(post, type_mesure):
    v = {}
    for cle, c in CHAMPS[type_mesure].items():
        if c['type'] == X:
            choix = [x for x in post.getlist(cle) if x in c['options']]
            if choix:
                v[cle] = choix
        else:
            x = (post.get(cle) or '').strip()[:6000]
            if x:
                v[cle] = x
    return v


def pour_gabarit(a):
    v = a.donnees or {}
    return [(t, [dict(c, valeur=v.get(c['cle'], [] if c['type'] == X else '')) for c in cs])
            for t, cs in SECTIONS[a.type_mesure]]


def manques(a):
    """Ce qu'il faut avant l'envoi."""
    out = []
    if not a.nom_operateur:
        out.append("Choisissez l'opérateur sollicité.")
    if not (a.donnees or {}).get('evaluation'):
        out.append("Rédigez l'évaluation du travailleur social.")
    return out


# ------------------------------------------------------------------------------------------------- circuit
def creer(b, user, type_mesure, volet, dossier_expulsion=None):
    a = A(beneficiaire=b, mds=b.mds, type_mesure=type_mesure, volet=volet, dossier_expulsion=dossier_expulsion, cree_par=user)
    a.donnees = preremplir(a, user)
    a.tracer(user, "Fiche créée (préremplie)")
    a.save()
    if dossier_expulsion:
        dossier_expulsion.tracer(user, "Orientation ASELL préparée", a.get_type_mesure_display())
        dossier_expulsion.save()
    return a


def marquer_envoyee(a, user, mode):
    a.statut, a.date_envoi = A.ENVOYEE, timezone.localdate()
    a.tracer(user, "Envoyée" + (" par mail" if mode == 'MAIL' else " (imprimée)"), a.nom_operateur)
    a.save()
    if a.dossier_expulsion_id:
        a.dossier_expulsion.tracer(user, "Orientation ASELL envoyée", f"{a.get_type_mesure_display()} – {a.nom_operateur}")
        a.dossier_expulsion.save()


def enregistrer_reponse(a, user, issue, date_reponse, detail=""):
    a.reponse, a.date_reponse, a.reponse_detail = issue, date_reponse or timezone.localdate(), detail[:255]
    a.tracer(user, f"Réponse : {a.get_reponse_display().lower()}", detail[:200])
    a.save()


# ------------------------------------------------------------------------------------------------- PDF
def _t(x):
    return escape(str(x or "")).replace("\n", "<br/>")


def _coche(options, choisis):
    """Cases à cocher écrites en caractères simples : identiques sur tous les serveurs, sans police particulière."""
    choisis = choisis if isinstance(choisis, list) else [choisis]
    return " &nbsp; ".join((f"<b>[X] {_t(o)}</b>" if o in choisis else f"[&nbsp;&nbsp;] {_t(o)}") for o in options)


def fiche_pdf(a):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from AidFi.services.afase_pdf import draw_page_template, get_ditas_styles
    from mds.fonctions import fonction_de
    from .fsl import coordonnees_ts
    st, v, mds = get_ditas_styles(), a.donnees or {}, a.mds
    normal = ParagraphStyle("asell", parent=st["Normal"], fontSize=9, leading=12)
    P = lambda x: Paragraph(x, normal)                 # noqa: E731
    gras = lambda x: f"<b>{_t(x)}</b>"                 # noqa: E731

    def valeur(c):
        x = v.get(c['cle'])
        if c['type'] in (R, X):
            return _coche(c['options'], x or [])
        return _t(x)

    def tab(lignes):
        t = Table([[P(c) for c in l] for l in lignes], colWidths=[6.5 * cm, 11.5 * cm])
        t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        return t

    ts = a.cree_par
    c = coordonnees_ts(ts, mds) if ts else {}
    f = fonction_de(ts, mds) if ts else ""
    prescripteur = (f"{_t(mds.nom)} – {_t(ts.get_full_name() if ts else '')}" + (f", {_t(f)}" if f else "")
                    + f"<br/>{_t(' '.join(x for x in (mds.adresse, mds.code_postal, mds.ville) if x))}"
                    + (f"<br/>{_t(c.get('telephone'))}" if c.get('telephone') else "") + (f" – {_t(mds.email)}" if mds.email else ""))
    el = [Paragraph(f"FICHE D'ORIENTATION {_t(a.get_type_mesure_display().upper())}", st["TitreOfficiel"]),
          P(_coche([x for _, x in A.VOLETS], a.get_volet_display())),
          Spacer(1, 6),
          tab([[gras("Prescripteur"), prescripteur], [gras("Opérateur sollicité"), _t(a.nom_operateur)]]), Spacer(1, 6)]
    for titre, champs in SECTIONS[a.type_mesure]:
        if titre.startswith("Évaluation"):
            el += [Paragraph(titre.upper(), st["SectionHeader"]), P(_t(v.get('evaluation'))), Spacer(1, 10),
                   KeepTogether([P(f"Fait à {_t(v.get('fait_a'))}, le {(a.date_envoi or timezone.localdate()):%d/%m/%Y}"),
                                 P(f"{gras(ts.get_full_name() if ts else '')}" + (f", {_t(f)}" if f else ""))])]
            continue
        lignes = [[gras(c['label']), valeur(c)] for c in champs if c['type'] in (R, X) or v.get(c['cle'])]
        el += [KeepTogether([Paragraph(titre.upper(), st["SectionHeader"]), tab(lignes)]), Spacer(1, 4)]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=3.5 * cm, bottomMargin=2 * cm, leftMargin=1.5 * cm,
                            rightMargin=1.5 * cm, title=f"Orientation {a.get_type_mesure_display()}", author="CID")
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    return buf.getvalue()
