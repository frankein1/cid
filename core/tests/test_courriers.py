# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/tests/test_courriers.py
"""Moteur des modèles de courriers (sans base de données) : python manage.py test core.tests.test_courriers"""
from django.test import SimpleTestCase

from core.courriers import rendu
from core.courriers.registre import COURRIERS, exemple


class RenduTests(SimpleTestCase):
    def test_variables_gras_petit(self):
        p = rendu.paragraphes("Bonjour {nom},\n\n**{montant}** [petit]note[/petit]", {"nom": "A & B", "montant": "10 €"})
        self.assertEqual(p, ["Bonjour A &amp; B,", "<b>10 €</b> <font size=8>note</font>"])

    def test_condition_avec_variables(self):
        t = "{si_recours:demande du {d} et recours du {r}|demande du {d}}"
        self.assertEqual(rendu.ligne(t, {"d": "1/1", "r": "2/2"}, {"si_recours": True}), "demande du 1/1 et recours du 2/2")
        self.assertEqual(rendu.ligne(t, {"d": "1/1", "r": ""}, {"si_recours": False}), "demande du 1/1")

    def test_paragraphe_facultatif_supprime(self):
        p = rendu.paragraphes("A\n\nRecours : {voies}\n\n{si_x:texte}\n\nB", {"voies": ""}, {"si_x": False})
        self.assertEqual(p, ["A", "B"])

    def test_texte_saisi_echappe(self):
        self.assertEqual(rendu.ligne("<script> & {v}", {"v": "<b>"}), "&lt;script&gt; &amp; &lt;b&gt;")

    def test_retour_ligne_dans_paragraphe_et_valeur(self):
        self.assertEqual(rendu.ligne("a\nb {adr}", {"adr": "1 rue\n13000"}), "a<br/>b 1 rue<br/>13000")

    def test_erreurs(self):
        e = rendu.verifier("{inconnue} {si_zz:a} {si_ok:{x}|b}", {"x": ""}, {"si_ok": ""})
        self.assertIn("variable inconnue : {inconnue}", e)
        self.assertIn("condition inconnue : {si_zz:…}", e)
        self.assertEqual(len(e), 2)
        self.assertTrue(rendu.verifier("{si_ok:pas fermé", {}, {"si_ok": ""}))
        self.assertTrue(rendu.verifier("{si_ok:{si_ok:a}}", {}, {"si_ok": ""}))


class RegistreTests(SimpleTestCase):
    def test_textes_par_defaut_valides(self):
        for code, d in COURRIERS.items():
            for champ in ("objet", "corps", "signature"):
                with self.subTest(code=code, champ=champ):
                    self.assertEqual(rendu.verifier(d.get(champ, ""), d["variables"], d.get("conditions", {})), [])

    def test_exemples_sans_variable_restante(self):
        for code, d in COURRIERS.items():
            valeurs, conditions = exemple(code)
            texte = " ".join(rendu.paragraphes(d["corps"], valeurs, conditions))
            with self.subTest(code=code):
                self.assertNotRegex(texte, r"\{[A-Za-z_]+\}")
