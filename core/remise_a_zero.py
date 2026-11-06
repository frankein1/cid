# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/remise_a_zero.py
"""
REMISE À ZÉRO TOTALE de la base — VERSION DE DÉMONSTRATION UNIQUEMENT (à supprimer avant la mise en service).

Efface toutes les données de la base à laquelle CID est connecté (sur Render : celle de DATABASE_URL,
par exemple la base PostgreSQL d'alwaysdata), puis réinstalle : install, init2, init_demo.

Conservés :
  - les comptes super-administrateur (identifiant, mot de passe, nom, courriel), pour pouvoir se reconnecter ;
  - le paramétrage saisi en administration : référentiel AFASE (paramètres, motifs, montants indicatifs,
    motifs de refus et leurs textes), types de danger des IP, modèles de courriers, types d'actions d'insertion et
    actions d'insertion départementales et leurs questions, organismes de réorientation, paramètres du contrat RSA, configuration générale (clé / valeur).
    Les référentiels remplis par des migrations (motifs AFASE, motifs de refus, types de danger) doivent être
    dans MODELES_CONSERVES : « flush » vide aussi leurs tables, et les migrations déjà appliquées ne repassent pas.
Supprimés aussi : les fichiers de la GED (pCloud sur Render), document par document, avant l'effacement.

Garde-fous : super-administrateur + variable d'environnement CID_REMISE_A_ZERO_TOTALE=1 + confirmation tapée.
Exécutée dans un fil d'exécution à part (la requête web n'attend pas) ; l'avancement est écrit dans un
fichier du dossier temporaire, lisible par tous les processus du serveur.
"""
import json
import os
import tempfile
import threading
import traceback
from io import StringIO

from django.utils import timezone

FICHIER_ETAT = os.path.join(tempfile.gettempdir(), "cid_remise_a_zero.json")
# Sauvegarde du paramétrage et des super-administrateurs, écrite AVANT d'effacer la base. Si la remise à zéro
# échoue après l'effacement, la suivante repart de ce fichier (la base, vide, ne contient plus rien à sauver).
FICHIER_SAUVEGARDE = os.path.join(tempfile.gettempdir(), "cid_remise_a_zero_sauvegarde.json")
CONFIRMATION = "TOUT EFFACER"
# Paramétrage conservé (modèles sans lien vers les dossiers ; les liens vers un utilisateur sont vidés)
MODELES_CONSERVES = ["AidFi.ParametresAides", "AidFi.ReferentielMotifAFASE", "AidFi.MontantIndicatifAFASE",
                     "AidFi.MotifRefusAFASE", "protection_enfance.TypeDanger", "core.Configuration",
                     "core.ModeleCourrier", "insertion.TypeActionInsertion", "insertion.ActionInsertion",
                     "insertion.QuestionAction", "insertion.ParametresRSA", "insertion.OrganismeOrientation",
                     "beneficiaire.ValeurListe", "beneficiaire.TypeAccompagnement",
                     "connecteurs.MotifRDVSP"]
# Lignes conservées d'un modèle (par défaut toutes). Les actions locales, liées à une MDS effacée, ne le sont pas.
FILTRES_CONSERVES = {"insertion.ActionInsertion": lambda qs: qs.filter(niveau="DEPARTEMENTAL"),
                     "insertion.QuestionAction": lambda qs: qs.filter(action__niveau="DEPARTEMENTAL")}
DUREE_MAX_MINUTES = 30   # au-delà, une remise « en cours » est considérée comme interrompue (redémarrage du serveur)


def autorisee():
    return os.environ.get("CID_REMISE_A_ZERO_TOTALE", "").strip() == "1"


def lire_etat():
    try:
        with open(FICHIER_ETAT, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _ecrire_etat(etat):
    tmp = FICHIER_ETAT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False)
    os.replace(tmp, FICHIER_ETAT)


def en_cours():
    etat = lire_etat()
    if not etat or etat.get("etat") != "en_cours":
        return False
    debut = timezone.datetime.fromisoformat(etat["debut"])
    return (timezone.now() - debut).total_seconds() < DUREE_MAX_MINUTES * 60


def lancer(utilisateur):
    """Démarre la remise à zéro en arrière-plan. Renvoie False si une remise est déjà en cours."""
    if en_cours():
        return False
    qui = utilisateur.get_full_name() or utilisateur.username
    _ecrire_etat({"etat": "en_cours", "debut": timezone.now().isoformat(), "par": qui, "journal": ""})
    threading.Thread(target=_executer, args=(qui,), daemon=True, name="cid-remise-a-zero").start()
    return True


class _Journal:
    def __init__(self, etat):
        self.etat, self.lignes = etat, []

    def __call__(self, texte):
        self.lignes.append(texte)
        self.etat["journal"] = "\n".join(self.lignes)
        _ecrire_etat(self.etat)


def _executer(qui):
    from django.db import connection
    etat = lire_etat() or {"etat": "en_cours", "debut": timezone.now().isoformat(), "par": qui}
    journal = _Journal(etat)
    try:
        _remise_a_zero(journal)
        etat["etat"] = "termine"
        journal("🎉 Remise à zéro terminée.")
    except Exception as e:
        etat["etat"] = "echec"
        journal(f"❌ Échec : {e}\n{traceback.format_exc()}")
    finally:
        etat["fin"] = timezone.now().isoformat()
        _ecrire_etat(etat)
        connection.close()


def _commande(journal, nom, **options):
    from django.core.management import call_command
    sortie = StringIO()
    journal(f"▶ {nom}")
    call_command(nom, stdout=sortie, stderr=sortie, **options)
    lignes = [l for l in sortie.getvalue().splitlines() if l.strip()]
    if lignes:
        journal("\n".join("   " + l for l in lignes[-15:]))


def _remise_a_zero(journal):
    from django.apps import apps
    from django.core import serializers
    from django.core.management import call_command
    from django.core.management.color import no_style
    from django.db import connection, transaction
    from core.models import User
    from ged.models import DocumentGED

    # 1. Sauvegarde : super-administrateurs et paramétrage, dans un fichier, avant tout effacement
    import json
    sauvegarde = _reprendre_sauvegarde(journal)
    if sauvegarde is None:
        champs = [f.attname for f in User._meta.concrete_fields if not f.is_relation and not f.primary_key]
        sauvegarde = {
            "date": timezone.now().isoformat(),
            "admins": [{c: getattr(u, c) for c in champs} for u in User.objects.filter(is_superuser=True)],
            "modeles": {nom: json.loads(serializers.serialize(
                "json", FILTRES_CONSERVES.get(nom, lambda q: q)(apps.get_model(nom).objects.all())))
                for nom in MODELES_CONSERVES},
        }
        with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
            json.dump(sauvegarde, f, ensure_ascii=False, default=str)
    admins = sauvegarde["admins"]
    journal(f"💾 {len(admins)} compte(s) super-administrateur conservé(s) : {', '.join(a['username'] for a in admins)}")
    journal("💾 Paramétrage conservé : " + ", ".join(f"{n.split('.')[1]} ({len(v)})"
                                                   for n, v in sauvegarde["modeles"].items()))

    # 2. Fichiers de la GED : chaque suppression purge son fichier du stockage (signaux de ged/signals.py)
    docs = list(DocumentGED.objects.all())
    for doc in docs:
        doc.delete()
    journal(f"🗑️ {len(docs)} document(s) GED et leurs fichiers supprimés")

    # 3. Effacement de toutes les tables (les sessions aussi : tout le monde est déconnecté)
    call_command("flush", interactive=False, verbosity=0)
    journal("🧹 Base vidée")

    # 4. Super-administrateurs recréés tout de suite : on peut se reconnecter pendant la suite
    def remettre_admins():
        for a in admins:
            u = User.objects.filter(username=a["username"]).first() or User(username=a["username"])
            for c, v in a.items():
                setattr(u, c, v)
            u.save()
    remettre_admins()
    journal("👤 Comptes super-administrateur recréés (mêmes identifiants et mots de passe)")

    # 5. Paramétrage remis. Les liens vers des données effacées (utilisateurs, MDS, pôles, partenaires…) sont
    # vidés ; seuls restent les liens entre modèles conservés (ex. montant indicatif → motif AFASE).
    # label_lower garde l'application telle qu'elle est déclarée (« AidFi.referentielmotifafase ») : on compare
    # donc avec les label_lower des modèles, pas avec les noms de MODELES_CONSERVES mis en minuscules.
    gardes = {apps.get_model(n)._meta.label_lower for n in MODELES_CONSERVES}
    echecs = []
    for nom, objets in sauvegarde["modeles"].items():
        modele = apps.get_model(nom)
        try:
            with transaction.atomic():
                for o in objets:
                    for champ in list(modele._meta.concrete_fields) + list(modele._meta.many_to_many):
                        if champ.is_relation and champ.related_model._meta.label_lower not in gardes:
                            o["fields"].pop(champ.name, None)
                for obj in serializers.deserialize("python", objets):
                    obj.save()
        except Exception as e:   # un modèle qui échoue n'empêche ni les autres, ni la réinstallation
            echecs.append(nom)
            journal(f"⚠️ {nom.split('.')[1]} non remis ({e.__class__.__name__} : {e})")
    with connection.cursor() as cur:   # compteurs d'identifiants remis après les numéros restaurés
        for sql in connection.ops.sequence_reset_sql(no_style(), [apps.get_model(n) for n in MODELES_CONSERVES]):
            cur.execute(sql)
    journal("⚙️ Paramétrage remis en place" + (f", sauf : {', '.join(n.split('.')[1] for n in echecs)}"
                                               f" (sauvegarde gardée : {FICHIER_SAUVEGARDE})" if echecs else ""))

    # 6. Réinstallation
    _commande(journal, "install", no_input=True)
    _commande(journal, "init2")
    _commande(journal, "init_demo")
    remettre_admins()   # au cas où init2 aurait le même identifiant qu'un super-administrateur
    if not echecs:
        os.remove(FICHIER_SAUVEGARDE)


def _reprendre_sauvegarde(journal):
    """Sauvegarde d'une remise à zéro précédente qui a échoué après l'effacement : elle seule contient encore
    le paramétrage. Sinon None (on sauvegarde la base actuelle)."""
    import json
    if not os.path.exists(FICHIER_SAUVEGARDE):
        return None
    try:
        with open(FICHIER_SAUVEGARDE, encoding="utf-8") as f:
            sauvegarde = json.load(f)
    except (OSError, ValueError):
        return None
    journal(f"↩️ Reprise de la sauvegarde du {sauvegarde.get('date', '?')[:16].replace('T', ' à ')} "
            "(la remise à zéro précédente n'est pas allée au bout)")
    return sauvegarde
