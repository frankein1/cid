# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/captures.py
"""
Captures d'écran des fiches d'aide « Bénéficiaires » (Playwright), sur la base de démonstration (init_demo),
avec runserver sur 127.0.0.1:8055 et les comptes de démonstration (docs/DONNEES_FICTIVES.md).
TW : dossier d'une compilation Tailwind locale (out.css et Font Awesome), car les captures se font hors ligne.
"""
import os
from playwright.sync_api import sync_playwright
from PIL import Image
B='http://127.0.0.1:8055'; RAW='/tmp/captures_aide'; OUT=str(__import__('pathlib').Path(__file__).resolve().parent.parent / 'img')
TW=os.environ.get('TW', '/tmp/tw'); FA=f'{TW}/node_modules/@fortawesome/fontawesome-free'
css=open(f'{TW}/out.css').read()
STYLE=".cid-hl{outline:4px solid #dc2626 !important;outline-offset:4px;border-radius:8px}"
HL="""(sel)=>{document.querySelectorAll('.cid-hl').forEach(e=>e.classList.remove('cid-hl'));
 if(!sel) return true; const e=document.querySelector(sel); if(!e) return false; e.classList.add('cid-hl'); e.scrollIntoView({block:'center'}); return true;}"""
os.makedirs(RAW, exist_ok=True)

class Cam:
    def __init__(s, p):
        s.b=p.chromium.launch()
    def page(s, user):
        ctx=s.b.new_context(viewport={'width':1280,'height':760}, locale='fr-FR', timezone_id='Europe/Paris')
        pg=ctx.new_page()
        def route(r):
            u=r.request.url
            if 'webfonts' in u: return r.fulfill(path=f"{FA}/webfonts/{u.split('/')[-1].split('?')[0]}")
            if '127.0.0.1' in u: return r.continue_()
            return r.abort()
        pg.route('**/*', route)
        pg.goto(B+'/login/'); pg.fill('input[name=username]',user); pg.fill('input[name=password]','demo123&')
        pg.click('form:has(input[name=username]) button[type=submit], form:has(input[name=username]) input[type=submit]')
        return pg
def prep(pg):
    pg.add_style_tag(content=css); pg.add_style_tag(path=f'{FA}/css/all.min.css'); pg.add_style_tag(content=STYLE); pg.wait_for_timeout(250)
def shot(pg, fiche, n, sel=None, top=False, element=None):
    prep(pg)
    assert pg.evaluate(HL, sel), (fiche, n, sel)
    if top: pg.evaluate('window.scrollTo(0,0)')
    pg.wait_for_timeout(150)
    os.makedirs(f'{OUT}/{fiche}', exist_ok=True)
    raw=f'{RAW}/{fiche}_{n}.png'
    if element: pg.locator(element).first.screenshot(path=raw)
    else: pg.screenshot(path=raw)
    Image.open(raw).convert('RGB').save(f'{OUT}/{fiche}/{n}.jpg', quality=82, optimize=True)
    print('ok', fiche, n)
def soumettre(pg, form_sel):
    pg.click(f'{form_sel} button[type=submit]'); pg.wait_for_load_state()

with sync_playwright() as p:
    cam=Cam(p)
    # ---------------- se connecter (page publique)
    pg=cam.b.new_page(viewport={'width':1280,'height':760}, locale='fr-FR')
    pg.route('**/*', lambda r: r.continue_() if '127.0.0.1' in r.request.url else r.abort())
    pg.goto(B+'/login/'); prep(pg); pg.fill('input[name=username]','as1_mds1'); shot(pg,'connexion','01','input[name=username]')
    pg.goto(B+'/mot-de-passe-oublie/'); pg.fill('input[name=identifiant]','as1_mds1'); shot(pg,'connexion','02','input[name=identifiant]')
    pg.click('form button[type=submit]'); pg.wait_for_load_state(); shot(pg,'connexion','03')
    # mot de passe provisoire : changement obligatoire (compte as2_mds1 réinitialisé avant la capture)
    pv=cam.b.new_page(viewport={'width':1280,'height':760}, locale='fr-FR')
    pv.route('**/*', lambda r: r.continue_() if '127.0.0.1' in r.request.url else r.abort())
    pv.goto(B+'/login/'); pv.fill('input[name=username]','as2_mds1'); pv.fill('input[name=password]', os.environ.get('MDP_PROVISOIRE','')); pv.click('form:has(input[name=username]) button[type=submit]')
    pv.wait_for_load_state(); shot(pv,'connexion','04','input[name=old_password]')
    # ---------------- chercher
    pg=cam.page('as1_mds1')
    prep(pg); pg.click('#ben-button'); pg.wait_for_timeout(200); shot(pg,'chercher','01','#ben-menu a[href$="/beneficiaire/"]')
    pg.goto(B+'/beneficiaire/'); pg.fill('input[name=nom]','GARNIER'); shot(pg,'chercher','02','input[name=nom]')
    pg.press('input[name=nom]','Enter'); pg.wait_for_load_state(); shot(pg,'chercher','03','tr.cursor-pointer')
    pg.goto(B+'/beneficiaire/FAM9-CEL/'); shot(pg,'chercher','04', None, top=True)
    # ---------------- créer
    pg.goto(B+'/beneficiaire/'); pg.fill('input[name=nom]','FONTAINE'); pg.press('input[name=nom]','Enter'); pg.wait_for_load_state()
    shot(pg,'creer','01','a[href$="/beneficiaire/ajouter/"].bg-green-600')
    pg.goto(B+'/beneficiaire/ajouter/')
    pg.select_option('select[name=civilite]','MME'); pg.fill('input[name=nom]','FONTAINE'); pg.fill('input[name=prenom]','Inès')
    pg.select_option('select[name=marital_status]','CELIBATAIRE'); pg.fill('input[name=date_naissance]','14/03/1991')
    pg.fill('input[name=lieu_naissance]','Martigues'); pg.fill('input[name=telephone_mobile]','0600000000')
    pg.fill('textarea[name=adresse]','4 allée des Mimosas'); pg.fill('input[name=code_postal]','13110'); pg.fill('input[name=ville]','Port-de-Bouc')
    pg.select_option('select[name=mds]', index=1); pg.wait_for_timeout(500)
    shot(pg,'creer','02','select[name=civilite]'); shot(pg,'creer','03','#mainForm button[type=submit]')
    soumettre(pg,'#mainForm'); code=pg.url.rstrip('/').split('/')[-1]; assert code.startswith('BEN-'), pg.url
    shot(pg,'creer','04',None, top=True)
    # ---------------- famille
    shot(pg,'famille','01', f'a[href$="/beneficiaire/{code}/lien/ajouter/"]')
    pg.goto(f'{B}/beneficiaire/{code}/lien/ajouter/')
    pg.select_option('select[name=type_lien]','ENFANT'); pg.select_option('select[name=nouveau_civilite]','M.')
    pg.fill('input[name=nouveau_nom]','FONTAINE'); pg.fill('input[name=nouveau_prenom]','Yanis'); pg.fill('input[name=nouveau_date_naissance]','02/09/2016')
    if not pg.is_checked('input[name=vit_au_foyer]'): pg.check('input[name=vit_au_foyer]')
    pg.check('input[name=est_responsable_legal]')
    shot(pg,'famille','02','select[name=type_lien]'); shot(pg,'famille','03','input[name=nouveau_nom]')
    soumettre(pg,'form:has(select[name=type_lien])'); shot(pg,'famille','04',None, top=True)
    prep(pg); carte=pg.locator('text=Réseau Familial').first.locator('xpath=ancestor::div[contains(@class,"rounded")][1]')
    carte.scroll_into_view_if_needed(); carte.screenshot(path=f'{RAW}/famille_05.png'); Image.open(f'{RAW}/famille_05.png').convert('RGB').save(f'{OUT}/famille/05.jpg', quality=85)
    # ---------------- modifier
    pg.goto(f'{B}/beneficiaire/{code}/'); shot(pg,'modifier','01', f'a[href$="/beneficiaire/{code}/modifier/"]')
    pg.goto(f'{B}/beneficiaire/{code}/modifier/'); pg.fill('input[name=telephone_mobile]','0611223344')
    shot(pg,'modifier','02','input[name=telephone_mobile]')
    pg.fill('input[name=numero_caf]','1234567'); shot(pg,'modifier','03','input[name=numero_caf]')
    soumettre(pg,'#formModifier'); shot(pg,'modifier','04',None, top=True)
    # ---------------- sortie
    shot(pg,'sortie','01', f'a[href$="/beneficiaire/{code}/sortir/"]')
    shot(pg,'sortie','04', f'a[href$="/beneficiaire/{code}/deces/"]')
    pg.goto(f'{B}/beneficiaire/{code}/sortir/'); pg.fill('input[name=date_sortie]','31/10/2026'); pg.select_option('select[name=motif_sortie]','DEMENAGEMENT')
    pg.fill('textarea[name=detail_sortie]',"Déménagement dans le Var (fictif).")
    shot(pg,'sortie','02','select[name=motif_sortie]')
    soumettre(pg,'form:has(select[name=motif_sortie])'); shot(pg,'sortie','03',None, top=True)
    shot(pg,'sortie','05', f'a[href$="/beneficiaire/{code}/reactiver/"]')
    pg.goto(f'{B}/beneficiaire/{code}/reactiver/'); shot(pg,'sortie','06','form button[type=submit].bg-green-600')
    # ---------------- transférer (agent de la MDS TEST 02)
    pg=cam.page('as1_mds2')
    pg.goto(B+'/beneficiaire/FAM6-KEV/'); shot(pg,'transferer','01','a[href$="/beneficiaire/FAM6-KEV/transferer/"]')
    pg.goto(B+'/beneficiaire/FAM6-KEV/transferer/'); shot(pg,'transferer','02','select[name=mds_destination]')
    shot(pg,'transferer','03','form button[type=submit].bg-amber-600')
    pg.click('form button[type=submit].bg-amber-600'); pg.wait_for_load_state(); shot(pg,'transferer','04',None, top=True)
    print('code créé', code)
