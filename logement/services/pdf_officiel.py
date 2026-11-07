# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/services/pdf_officiel.py
"""Écrire des données sur un formulaire PDF officiel non remplissable, en gardant sa pagination.

Chaque champ est placé par rapport à un libellé imprimé du formulaire (son « ancre ») : CID cherche ce libellé dans
le PDF déposé en administration et écrit à côté (après, dessous, dans une case, dans une cellule de tableau).
Si le gestionnaire change de logo ou décale un peu sa mise en page, les libellés restent et les champs suivent.
Un champ dont l'ancre est introuvable est simplement laissé vide ; l'aperçu de l'administration le signale."""
import io
import re

from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

POLICE = "Helvetica"


def _motif(ancre):
    morceaux = []
    for c in ancre:
        if c in "'’":
            morceaux.append("['’]")
        elif c == ' ':
            morceaux.append(r"\s*")
        else:
            morceaux.append(re.escape(c))
    return "".join(morceaux)


class _Recherche:
    def __init__(self, pdf):
        self.pdf = pdf
        self.cache = {}

    def toutes(self, page, ancre):
        cle = (page, ancre)
        if cle not in self.cache:
            try:
                self.cache[cle] = sorted(self.pdf.pages[page].search(_motif(ancre), regex=True, case=True),
                                         key=lambda m: (round(m['top']), m['x0']))
            except Exception:
                self.cache[cle] = []
        return self.cache[cle]

    def trouver(self, champ, ancre=None, page=None):
        ancre = ancre or champ['ancre']
        pages = [champ['page']] if page is None and champ.get('page') is not None else (
            [page] if page is not None else range(len(self.pdf.pages)))
        occ = champ.get('occ', 0)
        for p in pages:
            res = [m for m in self.toutes(p, ancre)
                   if champ.get('x_min', -1) <= m['x0'] <= champ.get('x_max', 1e6)
                   and champ.get('top_min', -1) <= m['top'] <= champ.get('top_max', 1e6)]
            if len(res) > occ:
                return p, res[occ]
        return None, None


def _ecrire(c, x, y, texte, taille, largeur=None, lignes=1, interligne=None):
    texte = str(texte).replace('’', "'").replace(' ', ' ')
    c.setFont(POLICE, taille)
    if not largeur:
        c.drawString(x, y, texte)
        return
    pas = interligne or taille * 1.25
    morceaux = []
    for paragraphe in texte.split("\n"):
        morceaux += simpleSplit(paragraphe, POLICE, taille, largeur) or [""]
    for i, ligne in enumerate(morceaux[:lignes]):
        c.drawString(x, y - i * pas, ligne)


def remplir(contenu_pdf, champs, valeurs, reglages=None):
    """Retourne (pdf rempli en octets, rapport {cle: 'ok' | 'ancre introuvable' | 'vide'})."""
    import pdfplumber
    from pypdf import PdfReader, PdfWriter
    reglages = reglages or {}
    rapport = {}
    ecritures = {}     # page -> [(x, y_depuis_le_haut, texte, champ)]
    with pdfplumber.open(io.BytesIO(contenu_pdf)) as pdf:
        tailles = [(p.width, p.height) for p in pdf.pages]
        r = _Recherche(pdf)
        for champ in champs:
            cle = champ['cle']
            valeur = valeurs.get(cle)
            if valeur in (None, '', False, [], {}):
                rapport[cle] = 'vide'
                continue
            regl = reglages.get(cle) or {}
            if 'x' in regl and 'y' in regl:
                page, x, y = regl.get('page', 0), regl['x'], regl['y']
            else:
                page, m = r.trouver(champ)
                if m is None:
                    rapport[cle] = 'ancre introuvable'
                    continue
                mode = champ.get('mode', 'apres')
                dx, dy = champ.get('dx', 0) + regl.get('dx', 0), champ.get('dy', 0) + regl.get('dy', 0)
                if mode == 'apres':
                    x, y = m['x1'] + 4 + dx, m['bottom'] - 2.5 + dy
                elif mode == 'dessous':
                    x, y = m['x0'] + dx, m['bottom'] + 11.5 + dy
                elif mode == 'case':
                    x, y = m['x0'] - 10 + dx, m['bottom'] - 1.5 + dy
                    valeur = "X"
                elif mode == 'case_dessous':
                    x, y = (m['x0'] + m['x1']) / 2 - 3 + dx, m['bottom'] + 11 + dy
                    valeur = "X"
                elif mode == 'cellule':
                    _, col = _colonne(r, page, champ, m)
                    if col is None:
                        rapport[cle] = 'colonne introuvable'
                        continue
                    x, y = col['x0'] + dx, m['bottom'] - 1 + dy
                else:
                    x, y = m['x0'] + dx, m['bottom'] + dy
            ecritures.setdefault(page, []).append((x, y, valeur, champ))
            rapport[cle] = 'ok'
    lecteur = PdfReader(io.BytesIO(contenu_pdf))
    sortie = PdfWriter()
    for i, page in enumerate(lecteur.pages):
        if i in ecritures:
            largeur, hauteur = tailles[i]
            tampon = io.BytesIO()
            c = canvas.Canvas(tampon, pagesize=(largeur, hauteur))
            c.setFillColorRGB(0.05, 0.15, 0.55)      # bleu : on voit ce que CID a écrit
            for x, y, texte, champ in ecritures[i]:
                _ecrire(c, x, hauteur - y, texte, champ.get('taille', 9), champ.get('largeur'), champ.get('lignes', 1),
                        champ.get('interligne'))
            c.save()
            tampon.seek(0)
            page.merge_page(PdfReader(tampon).pages[0])
        sortie.add_page(page)
    out = io.BytesIO()
    sortie.write(out)
    return out.getvalue(), rapport


def _colonne(r, page, champ, ligne):
    """En-tête de colonne le plus proche au-dessus de la ligne du tableau."""
    candidats = [m for m in r.toutes(page, champ['col']) if m['top'] < ligne['top']
                 and champ.get('col_x_min', -1) <= m['x0'] <= champ.get('col_x_max', 1e6)]
    if not candidats:
        return None, None
    return page, max(candidats, key=lambda m: m['top'])
