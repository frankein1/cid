# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/services/cap.py
"""
Logique métier des CAP (chèques service) : stock, composition, remise,
feuille de remise PDF, bordereau de réception PDF, clôture, incidents.

Les vues (AidFi/views/v_cap.py) ne font qu'appeler ces fonctions.
"""

import re
from io import BytesIO

from django.db import transaction
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from AidFi.models.m_cap import TitreCAP, VALEURS_CAP, InventaireCAP
from AidFi.services.afase_pdf import get_ditas_styles, draw_page_template


# =============================================================================
# STOCK
# =============================================================================

def titres_disponibles(mds):
    """
    Titres au coffre, non périmés, à distribuer en priorité :
    d'abord le reliquat des réceptions les plus anciennes (M-1), puis celles du mois.
    """
    return TitreCAP.objects.filter(
        mds=mds, statut='EN_STOCK', date_validite__gte=timezone.localdate()
    ).order_by('reception__date_reception', 'reception_id', 'numero')


def etat_stock(mds):
    """Résumé du coffre par valeur : disponibles et périmés encore au coffre."""
    aujourd_hui = timezone.localdate()
    lignes = []
    for v in VALEURS_CAP:
        qs = TitreCAP.objects.filter(mds=mds, statut='EN_STOCK', valeur=v)
        dispo = qs.filter(date_validite__gte=aujourd_hui).count()
        perimes = qs.filter(date_validite__lt=aujourd_hui).count()
        lignes.append({'valeur': v, 'disponibles': dispo, 'perimes': perimes,
                       'montant': dispo * v})
    return {
        'lignes': lignes,
        'total_disponible': sum(l['montant'] for l in lignes),
        'total_perimes': sum(l['perimes'] for l in lignes),
    }


def proposer_composition(mds, montant):
    """
    Propose des titres précis pour atteindre 'montant' avec le moins de titres possible,
    en tenant compte du stock réel. Retourne une liste de TitreCAP, ou None si impossible.
    """
    montant = int(montant or 0)
    if montant <= 0 or montant % 10:
        return None
    dispo = {v: list(titres_disponibles(mds).filter(valeur=v)) for v in VALEURS_CAP}
    c10, c20, c30 = len(dispo[10]), len(dispo[20]), len(dispo[30])
    for n30 in range(min(c30, montant // 30), -1, -1):
        reste30 = montant - 30 * n30
        for n20 in range(min(c20, reste30 // 20), -1, -1):
            reste = reste30 - 20 * n20
            if reste % 10 == 0 and reste // 10 <= c10:
                return dispo[30][:n30] + dispo[20][:n20] + dispo[10][:reste // 10]
    return None


def lire_numeros(texte):
    """Découpe une saisie (douchette ou clavier) en numéros, sans doublon, dans l'ordre."""
    vus, numeros = set(), []
    for n in re.split(r'[\s,;]+', texte or ''):
        n = n.strip()
        if n and n not in vus:
            vus.add(n)
            numeros.append(n)
    return numeros


# =============================================================================
# REMISE
# =============================================================================

@transaction.atomic
def enregistrer_remise(demande, numeros, cadre, agent_receveur):
    """
    Remise des chèques par le cadre à l'AS. Vérifie chaque titre scanné.
    Retourne la liste des erreurs (vide si la remise est enregistrée).
    """
    erreurs = []
    if demande.statut != 'ACCORDEE':
        return ["Cette demande n'est pas en attente de remise."]
    if not numeros:
        return ["Aucun numéro de chèque saisi."]

    titres = {t.numero: t for t in TitreCAP.objects.select_for_update().filter(numero__in=numeros)}
    aujourd_hui = timezone.localdate()
    for n in numeros:
        t = titres.get(n)
        if t is None:
            erreurs.append(f"{n} : numéro inconnu (non enregistré au coffre).")
        elif t.mds_id != demande.mds.pk:
            erreurs.append(f"{n} : ce chèque appartient au coffre d'une autre MDS.")
        elif t.statut != 'EN_STOCK':
            erreurs.append(f"{n} : chèque non disponible ({t.get_statut_display().lower()}).")
        elif t.date_validite < aujourd_hui:
            erreurs.append(f"{n} : chèque périmé depuis le {t.date_validite:%d/%m/%Y}.")
    if erreurs:
        return erreurs

    total = sum(titres[n].valeur for n in numeros)
    if total != demande.montant_accorde:
        return [f"Total scanné : {total} € — montant accordé : {demande.montant_accorde} €."]

    maintenant = timezone.now()
    for n in numeros:
        t = titres[n]
        t.statut = 'REMIS'
        t.demande = demande
        t.date_remise = maintenant
        t.remis_par = cadre
        t.remis_a = agent_receveur
        t.save()

    demande.statut = 'REMISE'
    demande.date_remise = maintenant
    demande.remis_par = cadre
    demande.remis_a = agent_receveur
    demande._acteur = cadre
    demande.save()
    return []


def enregistrer_remise_paierie(demande, numeros_texte, regisseur):
    """Remise faite par la paierie : pas de stock MDS, numéros notés pour mémoire."""
    demande.statut = 'REMISE'
    demande.date_remise = timezone.now()
    demande.remis_par = regisseur
    demande.numeros_paierie = "\n".join(lire_numeros(numeros_texte))
    demande._acteur = regisseur
    demande.save()


# =============================================================================
# CLÔTURE (feuille signée scannée → GED)
# =============================================================================

@transaction.atomic
def cloturer(demande, fichier, user, request=None):
    from ged.models import DocumentGED, DocumentType
    from AidFi.models.m_generique import PieceJustificative

    type_doc, _ = DocumentType.objects.get_or_create(
        code="CAP_REMISE",
        defaults={"nom": "Feuille de remise CAP signée", "categorie": "finances",
                  "extensions_autorisees": ["pdf", "jpg", "jpeg", "png"],
                  "taille_max_mb": 10, "est_sensible": True, "actif": True},
    )
    doc = DocumentGED.objects.create(
        content_object=demande.beneficiaire,
        type_document=type_doc,
        titre=f"Remise CAP signée - Dossier {demande.pk}",
        confidentialite="RESTREINT",
        uploaded_by=user,
    )
    doc.add_new_version(buffer=fichier, filename=fichier.name, user=user,
                        raison=f"Feuille de remise CAP dossier {demande.pk}", request=request)
    PieceJustificative.objects.create(demande=demande, document_ged=doc,
                                      type_piece='REMISE_CAP', statut='VALIDE', verifie_par=user,
                                      date_verification=timezone.now())

    demande.feuille_signee = doc
    demande.statut = 'CLOTUREE'
    demande.date_cloture = timezone.now()
    demande.cloture_par = user
    demande._acteur = user
    demande.save()
    return doc


# =============================================================================
# INCIDENTS (perte, vol, retour)
# =============================================================================

@transaction.atomic
def declarer_incident(titre, statut, user, commentaire):
    """
    Perte / vol / retour d'un chèque AU COFFRE (un chèque remis à l'usager ne nous concerne plus).
    Le stock relève du seul régisseur : il est prévenu, sauf s'il fait lui-même la déclaration.
    """
    from messagerie.models import Message, StatutLecture

    titre.statut = statut
    titre.date_incident = timezone.now()
    titre.incident_par = user
    titre.incident_commentaire = commentaire
    titre.save()

    if statut not in ('PERDU', 'VOLE'):
        return
    regisseur = titre.mds.regisseur
    for dest in ([regisseur] if regisseur and regisseur != user else []):
        msg = Message.objects.create(
            expediteur=user, destinataire=dest,
            objet=f"⚠️ Chèque service {titre.get_statut_display().lower()} : n° {titre.numero} ({titre.valeur} €)",
            contenu=(f"Le chèque service n° {titre.numero} ({titre.valeur} €) du coffre de {titre.mds} "
                     f"a été déclaré {titre.get_statut_display().lower()} le "
                     f"{timezone.localtime():%d/%m/%Y à %H:%M} par {user.get_full_name() or user.username}.\n\n"
                     f"Commentaire : {commentaire or '-'}\n\nMessage automatique de CID."),
            motif='signalement', priorite='urgente', reference=f"CAP-{titre.numero}",
        )
        StatutLecture.objects.create(message=msg, utilisateur=dest, type_reception='destinataire')


# =============================================================================
# INVENTAIRE DU COFFRE
# =============================================================================

def bilan_comptable(mds):
    """
    Pour chaque valeur : reçus - remis - perdus/volés - retournés = stock théorique au coffre.
    """
    lignes = []
    for v in VALEURS_CAP:
        qs = TitreCAP.objects.filter(mds=mds, valeur=v)
        recus = qs.count()
        remis = qs.filter(statut='REMIS').count()
        pertes = qs.filter(statut__in=('PERDU', 'VOLE')).count()
        retournes = qs.filter(statut='RETOURNE').count()
        stock = qs.filter(statut='EN_STOCK').count()
        lignes.append({'valeur': v, 'recus': recus, 'remis': remis, 'pertes': pertes,
                       'retournes': retournes, 'stock': stock})
    total = {k: sum(l[k] * l['valeur'] for l in lignes) for k in ('recus', 'remis', 'pertes', 'retournes', 'stock')}
    return {'lignes': lignes, 'total': total}


def _info_titre(t):
    return {'numero': t.numero, 'valeur': t.valeur, 'statut': t.get_statut_display(),
            'reception': t.reception.date_reception.strftime('%d/%m/%Y'),
            'validite': t.date_validite.strftime('%d/%m/%Y'), 'perime': t.est_perime,
            'demande': t.demande_id,
            'detail': (f"remis le {timezone.localtime(t.date_remise):%d/%m/%Y} par "
                       f"{_nom(t.remis_par)} à {_nom(t.remis_a)}") if t.statut == 'REMIS' else
                      (f"le {timezone.localtime(t.date_incident):%d/%m/%Y} par {_nom(t.incident_par)}"
                       if t.date_incident else '')}


def comparer_inventaire(inventaire):
    """
    Compare les chèques scannés au coffre et le stock théorique (statut « au coffre ») :
    - presents   : attendus et trouvés
    - manquants  : attendus mais NON trouvés → écart
    - inattendus : trouvés mais pas attendus (inconnus, autre MDS, déjà remis / perdus / retournés)
    """
    mds = inventaire.mds
    scannes = list(dict.fromkeys(inventaire.numeros or []))
    attendus = {t.numero: t for t in TitreCAP.objects.filter(mds=mds, statut='EN_STOCK').select_related('reception')}
    connus = {t.numero: t for t in TitreCAP.objects.filter(numero__in=scannes)
              .select_related('reception', 'mds', 'remis_par', 'remis_a', 'incident_par')}

    presents, inattendus = [], []
    for n in scannes:
        if n in attendus:
            presents.append(_info_titre(attendus[n]))
        elif n in connus:
            t = connus[n]
            info = _info_titre(t)
            info['motif'] = (f"chèque du coffre de {t.mds}" if t.mds_id != mds.pk
                             else f"enregistré « {t.get_statut_display().lower()} »")
            inattendus.append(info)
        else:
            inattendus.append({'numero': n, 'valeur': None, 'motif': "numéro inconnu (jamais réceptionné)"})
    manquants = [_info_titre(t) for n, t in sorted(attendus.items()) if n not in set(scannes)]

    def somme(liste):
        return sum(i['valeur'] or 0 for i in liste)

    par_valeur = []
    for v in VALEURS_CAP:
        theorique = sum(1 for t in attendus.values() if t.valeur == v)
        compte = sum(1 for i in presents if i['valeur'] == v)
        par_valeur.append({'valeur': v, 'theorique': theorique, 'compte': compte,
                           'ecart': compte - theorique})
    return {
        'nb_scannes': len(scannes),
        'presents': presents, 'manquants': manquants, 'inattendus': inattendus,
        'perimes_presents': [i for i in presents if i['perime']],
        'par_valeur': par_valeur,
        'theorique_euros': sum(t.valeur for t in attendus.values()),
        'compte_euros': somme(presents),
        'manquant_euros': somme(manquants),
        'ecart': bool(manquants or inattendus),
    }


def terminer_inventaire(inventaire, user, commentaire=""):
    resultat = comparer_inventaire(inventaire)
    resultat.pop('presents')          # inutile de figer la liste complète
    resultat['date'] = timezone.localtime().strftime('%d/%m/%Y %H:%M')
    inventaire.resultat = resultat
    inventaire.termine = True
    inventaire.date_fin = timezone.now()
    inventaire.commentaire = commentaire
    inventaire.save()
    return resultat


# =============================================================================
# PDF
# =============================================================================

def _nom(u):
    return (u.get_full_name() or u.username) if u else "-"


def feuille_remise_pdf(demande):
    """Feuille de remise à signer : cadre, AS, usager."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=3.5 * cm, bottomMargin=2 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm)
    st = get_ditas_styles()
    b = demande.beneficiaire
    el = [
        Paragraph("FEUILLE DE REMISE DE CHÈQUES SERVICE", st["TitreOfficiel"]),
        Paragraph("Chèques d'Accompagnement Personnalisé – Alimentation, hygiène", st["Normal"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"<b>Dossier :</b> CAP-{demande.pk} &nbsp;&nbsp; <b>MDS :</b> {demande.mds or '-'}", st["Normal"]),
        Paragraph(f"<b>Bénéficiaire :</b> {b.prenom} {b.nom.upper()} ({b.code_interne})"
                  f"{' – né(e) le ' + b.date_naissance.strftime('%d/%m/%Y') if b.date_naissance else ''}", st["Normal"]),
        Paragraph(f"<b>Montant accordé :</b> {demande.montant_accorde} € &nbsp;&nbsp; "
                  f"<b>Décision :</b> {_nom(demande.decide_par)}"
                  f"{', le ' + timezone.localtime(demande.date_decision).strftime('%d/%m/%Y') if demande.date_decision else ''}",
                  st["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    if demande.remise_paierie:
        numeros = [(n, "") for n in demande.numeros_paierie.split()] or [("Remise par la paierie départementale", "")]
        lignes = [["N° du chèque", "Valeur"]] + [[n, v] for n, v in numeros]
    else:
        titres = list(demande.titres.order_by('valeur', 'numero'))
        lignes = [["N° du chèque", "Valeur"]] + [[t.numero, f"{t.valeur} €"] for t in titres]
        lignes.append(["TOTAL", f"{sum(t.valeur for t in titres)} €"])
    tab = Table(lignes, colWidths=[11 * cm, 4 * cm])
    tab.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    el += [tab, Spacer(1, 0.4 * cm)]
    if demande.date_remise:
        el.append(Paragraph(
            f"Chèques remis le {timezone.localtime(demande.date_remise):%d/%m/%Y à %H:%M} "
            f"par {_nom(demande.remis_par)} à {_nom(demande.remis_a)}.", st["Normal"]))
    el += [
        Spacer(1, 0.4 * cm),
        Paragraph("Ces chèques sont exclusivement destinés à l'achat de produits alimentaires et d'hygiène.",
                  st["Normal"]),
        Spacer(1, 0.8 * cm),
    ]
    sig = Table([["Le cadre", "L'assistant(e) social(e)", "Le bénéficiaire"],
                 ["Date et signature", "Date et signature", "Date et signature\n« Reçu les chèques ci-dessus »"],
                 ["\n\n\n\n", "", ""]],
                colWidths=[5.6 * cm] * 3)
    sig.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    el.append(sig)
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer


def bordereau_reception_pdf(reception):
    """Bordereau d'entrée au coffre : liste des numéros, totaux par valeur, signature du régisseur."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=3.5 * cm, bottomMargin=2 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm)
    st = get_ditas_styles()
    titres = list(reception.titres.order_by('valeur', 'numero'))
    el = [
        Paragraph("BORDEREAU DE RÉCEPTION DE CHÈQUES SERVICE", st["TitreOfficiel"]),
        Paragraph(f"<b>MDS :</b> {reception.mds} &nbsp;&nbsp; <b>Régisseur :</b> {_nom(reception.regisseur)}", st["Normal"]),
        Paragraph(f"<b>Date de réception :</b> {reception.date_reception:%d/%m/%Y} &nbsp;&nbsp; "
                  f"<b>Validité des titres :</b> {reception.date_validite:%d/%m/%Y}"
                  f"{' &nbsp;&nbsp; <b>Réf. :</b> ' + reception.reference if reception.reference else ''}",
                  st["Normal"]),
        Spacer(1, 0.4 * cm),
    ]
    resume = [["Valeur", "Nombre", "Montant"]]
    for v in VALEURS_CAP:
        n = sum(1 for t in titres if t.valeur == v)
        if n:
            resume.append([f"{v} €", str(n), f"{n * v} €"])
    resume.append(["TOTAL", str(len(titres)), f"{sum(t.valeur for t in titres)} €"])
    t1 = Table(resume, colWidths=[5 * cm] * 3)
    t1.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')]))
    el += [t1, Spacer(1, 0.5 * cm), Paragraph("<b>Détail des numéros</b>", st["Normal"]), Spacer(1, 0.2 * cm)]

    # 3 colonnes de numéros pour tenir sur peu de pages
    cellules = [f"{t.numero} ({t.valeur} €)" for t in titres]
    lignes = [cellules[i:i + 3] + [""] * (3 - len(cellules[i:i + 3])) for i in range(0, len(cellules), 3)]
    if lignes:
        t2 = Table(lignes, colWidths=[5.6 * cm] * 3)
        t2.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
                                ('FONTSIZE', (0, 0), (-1, -1), 8)]))
        el.append(t2)
    el += [Spacer(1, 1 * cm),
           Paragraph("Le régisseur – date et signature :", st["Normal"]), Spacer(1, 2 * cm)]
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer


def proces_verbal_inventaire_pdf(inventaire):
    """Procès-verbal d'inventaire du coffre (écarts détaillés), à signer par le régisseur."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=3.5 * cm, bottomMargin=2 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm)
    st = get_ditas_styles()
    r = inventaire.resultat if inventaire.termine else comparer_inventaire(inventaire)
    el = [
        Paragraph("PROCÈS-VERBAL D'INVENTAIRE – CHÈQUES SERVICE", st["TitreOfficiel"]),
        Paragraph(f"<b>MDS :</b> {inventaire.mds} &nbsp;&nbsp; <b>Régisseur :</b> {_nom(inventaire.regisseur)}", st["Normal"]),
        Paragraph(f"<b>Inventaire du :</b> {timezone.localtime(inventaire.date_debut):%d/%m/%Y à %H:%M}"
                  f"{'' if inventaire.termine else ' (en cours)'}", st["Normal"]),
        Spacer(1, 0.4 * cm),
    ]
    lignes = [["Valeur", "Stock théorique", "Compté", "Écart"]]
    for l in r['par_valeur']:
        lignes.append([f"{l['valeur']} €", str(l['theorique']), str(l['compte']), f"{l['ecart']:+d}"])
    lignes.append(["TOTAL", f"{r['theorique_euros']} €", f"{r['compte_euros']} €",
                   f"{r['compte_euros'] - r['theorique_euros']:+d} €"])
    t = Table(lignes, colWidths=[3.5 * cm, 4.5 * cm, 4 * cm, 4 * cm])
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                           ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                           ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')]))
    el += [t, Spacer(1, 0.5 * cm)]

    def section(titre, items, avec_motif=False):
        el.append(Paragraph(f"<b>{titre} ({len(items)})</b>", st["Normal"]))
        if not items:
            el.append(Paragraph("Aucun.", st["Normal"]))
        else:
            data = [["N°", "Valeur", "Réception" if not avec_motif else "Constat"]]
            for i in items:
                data.append([i['numero'], f"{i['valeur']} €" if i['valeur'] else "?",
                             i.get('motif') if avec_motif else i.get('reception', '')])
            tt = Table(data, colWidths=[6 * cm, 2.5 * cm, 7.5 * cm])
            tt.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
                                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]))
            el.append(tt)
        el.append(Spacer(1, 0.4 * cm))

    section("Chèques manquants (attendus au coffre, non trouvés)", r['manquants'])
    section("Chèques trouvés mais non attendus", r['inattendus'], avec_motif=True)
    section("Chèques périmés encore au coffre", r['perimes_presents'])
    if inventaire.commentaire:
        el.append(Paragraph(f"<b>Observations :</b> {inventaire.commentaire}", st["Normal"]))
    el += [Spacer(1, 1 * cm), Paragraph("Le régisseur – date et signature :", st["Normal"]), Spacer(1, 2 * cm)]
    doc.build(el, onFirstPage=draw_page_template, onLaterPages=draw_page_template)
    buffer.seek(0)
    return buffer

