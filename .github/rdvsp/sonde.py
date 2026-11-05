# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# .github/rdvsp/sonde.py
"""
Essai CID ↔ RDV-Solidarités, contre une VRAIE copie éphémère de RDV-Solidarités (données fictives).
Vérifie, avant d'écrire la passerelle, chaque point de l'API dont CID aura besoin :
lieux, motifs, permanences (récurrentes), absences, usagers, invitations, avis automatiques signés
(webhooks), statuts de RDV, renouvellement du jeton. Écrit un compte rendu (résumé GitHub + sortie).
"""
import hashlib
import hmac
import json
import os
import subprocess
import sys
import threading
import time
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

MRS = os.environ.get("MRS_URL", "http://localhost:3000")
MRS_DIR = os.environ["MRS_DIR"]
SEED = json.load(open(os.environ["SEED_JSON"]))
SECRET = "secret-webhook-essai"
PORT = 8099
API = f"{MRS}/api/v1"
ORG = SEED["organisation_id"]
resultats = []          # (étape, ok, détail)
recus = []              # avis automatiques reçus : (entêtes, corps brut)


def noter(etape, ok, detail=""):
    resultats.append((etape, ok, detail))
    print(("✅" if ok else "❌"), etape, "—", detail, flush=True)


class Recepteur(BaseHTTPRequestHandler):
    def do_POST(self):
        corps = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        recus.append((dict(self.headers), corps))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


def entetes(jeton=None):
    return {"Authorization": f"Bearer {jeton or SEED['jeton']}", "Accept": "application/json"}


def appel(methode, chemin, jeton=None, **kw):
    r = requests.request(methode, f"{API}{chemin}", headers=entetes(jeton), timeout=30, **kw)
    try:
        return r.status_code, (r.json() if r.content else {})
    except ValueError:
        return r.status_code, {"brut": r.text[:300]}


def rails(*args):
    p = subprocess.run(["bin/rails", "runner", "../.github/rdvsp/agir.rb", *map(str, args)], cwd=MRS_DIR,
                       capture_output=True, text=True, timeout=180)
    if p.returncode:
        raise RuntimeError((p.stderr or "")[-600:] + " | " + (p.stdout or "")[-300:])
    return json.loads(p.stdout.strip().splitlines()[-1])


def attendre_avis(condition, delai=90):
    fin = time.time() + delai
    while time.time() < fin:
        for h, corps in list(recus):
            try:
                d = json.loads(corps)
            except ValueError:
                continue
            if condition(d):
                return h, corps, d
        time.sleep(1)
    return None, None, None


def signature_ok(h, corps):
    attendu = hmac.new(SECRET.encode(), corps, hashlib.sha256).hexdigest()
    recu = {k.lower(): v for k, v in h.items()}.get("x-lapin-signature", "")
    return hmac.compare_digest(attendu, recu)


def lundi_prochain():
    j = date.today() + timedelta(days=7)
    return j - timedelta(days=j.weekday())


def etape(nom):
    def deco(f):
        def g(*a):
            try:
                return f(*a)
            except Exception as e:  # une étape ratée n'empêche pas les suivantes
                noter(nom, False, f"{type(e).__name__} : {e}"[:400])
        return g
    return deco


def main():
    serveur = HTTPServer(("0.0.0.0", PORT), Recepteur)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    ctx = {}

    @etape("1. Jeton OAuth de l'agent : /agents/me")
    def e1():
        c, d = appel("GET", "/agents/me")
        noter("1. Jeton OAuth de l'agent : /agents/me", c == 200, f"{c} agent={d.get('agent', {}).get('email')}")

    @etape("2. Déclarer l'adresse de CID (webhook) par l'API")
    def e2():
        c, d = appel("POST", f"/organisations/{ORG}/webhook_endpoints", json={
            "target_url": f"http://localhost:{PORT}/webhook", "secret": SECRET,
            "subscriptions": ["rdv", "absence", "plage_ouverture", "user", "motif", "lieu"]})
        noter("2. Déclarer l'adresse de CID (webhook) par l'API", c == 200, f"{c} {json.dumps(d)[:200]}")

    @etape("3. Créer le lieu (MDS) avec la référence CID")
    def e3():
        c, d = appel("POST", "/lieux", json={
            "organisation_id": ORG, "name": "MDS TEST 01 – Accueil", "address": "1 rue des Essais, 13110 Port-de-Bouc",
            "latitude": 43.405, "longitude": 4.987, "availability": "enabled",
            "external_reference": {"external_id": "cid-mds-1"}})
        ctx["lieu_id"] = (d.get("lieu") or d).get("id")
        noter("3. Créer le lieu (MDS) avec la référence CID", c == 200 and ctx["lieu_id"], f"{c} {json.dumps(d)[:250]}")

    @etape("4. Créer le motif « Renouvellement RSA » (invités seulement, 48 h – 15 jours)")
    def e4():
        corps = {"organisation_id": ORG, "name": "Renouvellement RSA", "color": "#1e3a8a",
                 "default_duration_in_min": 30, "min_public_booking_delay": 48 * 3600,
                 "max_public_booking_delay": 15 * 86400, "location_type": "public_office",
                 "bookable_by": "agents_and_prescripteurs_and_invited_users",
                 "service_id": SEED["service_id"], "external_reference": {"external_id": "cid-motif-rsa"}}
        c, d = appel("POST", "/motifs", json=corps)
        if c != 200:   # sans service_id, au cas où il ne serait pas accepté
            corps.pop("service_id")
            c, d = appel("POST", "/motifs", json=corps)
        m = d.get("motif") or d
        ctx["motif_id"] = m.get("id")
        noter("4. Créer le motif « Renouvellement RSA » (invités seulement, 48 h – 15 jours)", c == 200 and m.get("id"),
              f"{c} bookable_by={m.get('bookable_by')} délais={m.get('min_public_booking_delay')}/"
              f"{m.get('max_public_booking_delay')} {json.dumps(d)[:200] if c != 200 else ''}")

    @etape("5. Publier une permanence récurrente (lundi matin, chaque semaine)")
    def e5():
        lundi = lundi_prochain()
        recurrence = json.dumps({"every": "week", "on": ["monday"], "interval": 1, "starts": lundi.isoformat()})
        c, d = appel("POST", "/plage_ouvertures", json={
            "organisation_id": ORG, "agent_id": SEED["agent_id"], "title": "Permanence CID",
            "first_day": lundi.isoformat(), "start_time": "09:00", "end_time": "12:00",
            "lieu_external_id": "cid-mds-1", "motif_external_ids": ["cid-motif-rsa"], "recurrence": recurrence,
            "external_reference": {"external_id": "cid-permanence-1"}})
        p = d.get("plage_ouverture") or d
        ctx["lundi"] = lundi
        noter("5. Publier une permanence récurrente (lundi matin, chaque semaine)", c == 200 and p.get("id"),
              f"{c} récurrence={p.get('rrule') or p.get('recurrence')} motifs={[m.get('name') for m in p.get('motifs', [])]}"
              f" {json.dumps(d)[:300] if c != 200 else ''}")

    @etape("6. Absence : créer, modifier, supprimer (blocage d'une demi-journée)")
    def e6():
        jour = (ctx.get("lundi") or lundi_prochain()) + timedelta(days=7)
        c, d = appel("POST", "/absences", json={"agent_id": SEED["agent_id"], "title": "Quota en ligne atteint (CID)",
                                                 "first_day": jour.isoformat(), "start_time": "09:00", "end_time": "12:00"})
        a = d.get("absence") or {}
        c2, _ = appel("PATCH", f"/absences/{a.get('id')}", json={"end_time": "11:30"}) if a else (0, {})
        c3, _ = appel("DELETE", f"/absences/{a.get('id')}") if a else (0, {})
        noter("6. Absence : créer, modifier, supprimer (blocage d'une demi-journée)", (c, c2, c3) == (200, 200, 204),
              f"création {c}, modification {c2}, suppression {c3} {json.dumps(d)[:200] if c != 200 else ''}")

    @etape("7. Créer l'usager et son invitation")
    def e7():
        c, d = appel("POST", "/users", json={"organisation_ids": [ORG], "first_name": "Lucie", "last_name": "ESSAI",
                                              "email": "lucie.essai@exemple.test", "birth_date": "1990-01-01",
                                              "phone_number": "0611223344"})
        u = d.get("user") or {}
        ctx["user_id"] = u.get("id")
        c2, d2 = appel("POST", f"/users/{u.get('id')}/rdv_invitation_token") if u else (0, {})
        noter("7. Créer l'usager et son invitation", c == 200 and c2 == 200 and d2.get("invitation_token"),
              f"usager {c}, invitation {c2} (jeton {'reçu' if d2.get('invitation_token') else 'absent'})"
              f" {json.dumps(d)[:200] if c != 200 else ''}")

    @etape("8. L'usager réserve en ligne → CID est prévenu (avis signé)")
    def e8():
        debut = datetime.combine(ctx["lundi"] + timedelta(days=7), datetime.min.time()).replace(hour=9, minute=30)
        rdv = rails("reserver", ctx["user_id"], ctx["motif_id"], ctx["lieu_id"], SEED["agent_id"],
                    debut.isoformat() + "+01:00")
        ctx["rdv_id"] = rdv["rdv_id"]
        h, corps, d = attendre_avis(lambda x: x.get("meta", {}).get("model") == "Rdv"
                                    and x.get("data", {}).get("id") == ctx["rdv_id"])
        if not d:
            noter("8. L'usager réserve en ligne → CID est prévenu (avis signé)", False, "aucun avis reçu en 90 s")
            return
        r = d["data"]
        noter("8. L'usager réserve en ligne → CID est prévenu (avis signé)", signature_ok(h, corps),
              f"signature {'valide' if signature_ok(h, corps) else 'INVALIDE'}, événement={d['meta'].get('event')}, "
              f"créé par={r.get('created_by')}, motif={(r.get('motif') or {}).get('name')}, début={r.get('starts_at')}, "
              f"usagers={[u.get('id') for u in r.get('users', [])]}, lieu={(r.get('lieu') or {}).get('name')}")
        ctx["exemple_avis"] = d

    @etape("9. L'usager annule → CID reçoit l'heure d'annulation")
    def e9():
        rails("annuler", ctx["rdv_id"])
        h, corps, d = attendre_avis(lambda x: x.get("meta", {}).get("model") == "Rdv"
                                    and x.get("data", {}).get("id") == ctx["rdv_id"]
                                    and x.get("data", {}).get("status") == "excused")
        ok = bool(d) and bool(d["data"].get("cancelled_at"))
        noter("9. L'usager annule → CID reçoit l'heure d'annulation", ok,
              f"statut={d['data'].get('status') if d else '—'}, annulé le={d['data'].get('cancelled_at') if d else '—'}")

    @etape("10. CID lit les RDV de l'organisation")
    def e10():
        c, d = appel("GET", f"/organisations/{ORG}/rdvs")
        noter("10. CID lit les RDV de l'organisation", c == 200, f"{c} {len(d.get('rdvs', []))} RDV")

    @etape("11. CID change le statut d'un RDV (venu / absent)")
    def e11():
        debut = datetime.combine(ctx["lundi"] + timedelta(days=14), datetime.min.time()).replace(hour=10)
        rdv = rails("reserver", ctx["user_id"], ctx["motif_id"], ctx["lieu_id"], SEED["agent_id"],
                    debut.isoformat() + "+01:00")
        res = {}
        for statut in ("seen", "noshow", "revoked"):
            res[statut] = appel("PATCH", f"/rdvs/{rdv['rdv_id']}/update_status", json={"status": statut})[0]
        noter("11. CID change le statut d'un RDV (venu / absent)", any(v == 200 for v in res.values()),
              "codes : " + ", ".join(f"{k}={v}" for k, v in res.items()) + " (RDV à venir)")

    @etape("12. Avis reçus pour les permanences et absences")
    def e12():
        modeles = sorted({json.loads(c).get("meta", {}).get("model") for _, c in recus if c.startswith(b"{")})
        noter("12. Avis reçus pour les permanences et absences", "PlageOuverture" in modeles and "Absence" in modeles,
              f"modèles reçus : {modeles}")

    @etape("13. Renouveler le jeton OAuth")
    def e13():
        r = requests.post(f"{MRS}/oauth/token", data={
            "grant_type": "refresh_token", "refresh_token": SEED["jeton_renouvellement"],
            "client_id": SEED["client_id"], "client_secret": SEED["client_secret"]}, timeout=30)
        nouveau = r.json().get("access_token") if r.status_code == 200 else None
        c = appel("GET", "/agents/me", jeton=nouveau)[0] if nouveau else 0
        noter("13. Renouveler le jeton OAuth", r.status_code == 200 and c == 200,
              f"{r.status_code} expire dans {r.json().get('expires_in') if r.status_code == 200 else '—'} s ; nouveau jeton → {c}"
              + ("" if r.status_code == 200 else f" {r.text[:200]}"))

    for e in (e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12, e13):
        e()

    lignes = ["## Essai CID ↔ RDV-Solidarités (copie éphémère, données fictives)", "",
              "| Étape | Résultat | Détail |", "|---|---|---|"]
    lignes += [f"| {n} | {'✅' if ok else '❌'} | {str(d).replace('|', '/')} |" for n, ok, d in resultats]
    if ctx.get("exemple_avis"):
        lignes += ["", "<details><summary>Exemple d'avis automatique (RDV pris par l'usager)</summary>", "",
                   "```json", json.dumps(ctx["exemple_avis"], indent=2, ensure_ascii=False)[:6000], "```", "</details>"]
    rapport = "\n".join(lignes)
    print(rapport)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(rapport + "\n")
    open(os.environ.get("RAPPORT", "rapport_rdvsp.md"), "w").write(rapport + "\n")
    serveur.shutdown()
    sys.exit(0 if all(ok for _, ok, _ in resultats) else 1)


if __name__ == "__main__":
    main()
