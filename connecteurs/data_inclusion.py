# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/data_inclusion.py
"""
data·inclusion, étape 1 : import des FICHIERS OUVERTS (data.gouv.fr, Licence Ouverte 2.0, mis à jour chaque semaine),
sans jeton, filtrés sur les départements choisis (DATA_INCLUSION_DEPARTEMENTS, « 13 » par défaut), puis recherche
dans CID par thématique, commune, gratuité et mode d'accueil.

Rien n'est envoyé à data·inclusion : CID télécharge, filtre et garde la copie locale. Les fichiers sont lus en flux
(ligne par ligne), sans tout charger en mémoire.

Étape 2 (production, avec jeton) : recherche en direct par l'API — non faite ici.
"""
import ast
import csv
import io
import json
import logging
import math
import os
import threading
from datetime import date, timedelta

import requests
from django.db import transaction
from django.utils import timezone

log = logging.getLogger(__name__)

# Ressources stables du jeu de données (constants.py du pipeline data·inclusion)
URL_STRUCTURES = "https://www.data.gouv.fr/api/1/datasets/r/fd4cb3ef-5c31-4c99-92fe-2cd8016c0ca5"
URL_SERVICES = "https://www.data.gouv.fr/api/1/datasets/r/5abc151a-5729-4055-b0a9-d5691276f461"
csv.field_size_limit(10_000_000)


def departements():
    return [d.strip() for d in os.environ.get("DATA_INCLUSION_DEPARTEMENTS", "13").split(",") if d.strip()]


def liste(valeur):
    """Les listes arrivent écrites à la façon de Python (« ['a', 'b'] »), parfois en JSON ou séparées par des virgules."""
    if valeur is None:
        return []
    v = str(valeur).strip()
    if not v or v in ("[]", "None", "nan"):
        return []
    if v[0] in "[(":
        for lecteur in (json.loads, ast.literal_eval):
            try:
                res = lecteur(v)
                return [str(x).strip() for x in res if str(x).strip()]
            except (ValueError, SyntaxError, TypeError):
                continue
        v = v.strip("[]()")
        return [x.strip().strip("'\"") for x in v.replace("' '", "','").split(",") if x.strip().strip("'\"")]
    return [x.strip() for x in v.replace("|", ",").split(",") if x.strip()]


def _texte(v, n=None):
    v = "" if v is None or str(v) in ("nan", "None") else str(v).strip()
    return v[:n] if n else v


def _nombre(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def _date(v):
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _dans(departements_, code_postal, code_insee, zone):
    code = (code_insee or code_postal or "")
    if any(code.startswith(d) for d in departements_):
        return True
    return any(any(z == d or z.startswith(d) for d in departements_) for z in zone)


def lignes_csv(url, ouvrir=None):
    """Lit un CSV distant ligne par ligne (dictionnaires)."""
    if ouvrir:
        flux = ouvrir(url)
    else:
        r = requests.get(url, stream=True, timeout=(15, 300))
        r.raise_for_status()
        r.encoding = "utf-8"
        flux = r.iter_lines(decode_unicode=True)
    lecteur = csv.DictReader(_lignes_completes(flux))
    yield from lecteur


def _lignes_completes(flux):
    for ligne in flux:
        yield (ligne.decode("utf-8") if isinstance(ligne, bytes) else ligne) + "\n"


def importer(departements_=None, ouvrir=None, user=None):
    """Importe structures puis services du territoire ; retire les services disparus des fichiers. Retourne la trace."""
    from .models import ImportInclusion, ServiceInclusion
    departements_ = departements_ or departements()
    trace = ImportInclusion.objects.create(departements=",".join(departements_), lance_par=user)
    try:
        structures = {}
        for s in lignes_csv(URL_STRUCTURES, ouvrir):
            if _dans(departements_, _texte(s.get("code_postal")), _texte(s.get("code_insee")), []):
                structures[_texte(s.get("id"))] = s
        trace.structures = len(structures)
        vus = set()
        lot = []
        for s in lignes_csv(URL_SERVICES, ouvrir):
            zone = liste(s.get("zone_eligibilite"))
            st = structures.get(_texte(s.get("structure_id")))
            if not st and not _dans(departements_, _texte(s.get("code_postal")), _texte(s.get("code_insee")), zone):
                continue
            st = st or {}
            di_id = _texte(s.get("id"), 255)
            if not di_id or di_id in vus:
                continue
            vus.add(di_id)
            lot.append(ServiceInclusion(
                di_id=di_id, source=_texte(s.get("source"), 60), structure_id=_texte(s.get("structure_id"), 255),
                structure_nom=_texte(st.get("nom"), 255), structure_siret=_texte(st.get("siret"), 14),
                nom=_texte(s.get("nom"), 255) or "(sans nom)", description=_texte(s.get("description"), 5000),
                type=_texte(s.get("type"), 40), thematiques=liste(s.get("thematiques")), publics=liste(s.get("publics")),
                frais=_texte(s.get("frais"), 20), modes_accueil=liste(s.get("modes_accueil")),
                conditions_acces=_texte(s.get("conditions_acces"), 3000),
                adresse=_texte(s.get("adresse") or st.get("adresse"), 255),
                code_postal=_texte(s.get("code_postal") or st.get("code_postal"), 5),
                commune=_texte(s.get("commune") or st.get("commune"), 100),
                code_insee=_texte(s.get("code_insee") or st.get("code_insee"), 5),
                latitude=_nombre(s.get("latitude") or st.get("latitude")),
                longitude=_nombre(s.get("longitude") or st.get("longitude")),
                telephone=_texte(s.get("telephone") or st.get("telephone"), 40),
                courriel=_texte(s.get("courriel") or st.get("courriel"), 255),
                horaires_accueil=_texte(s.get("horaires_accueil") or st.get("horaires_accueil"), 2000),
                lien_source=_texte(s.get("lien_source"), 2083), lien_mobilisation=_texte(s.get("lien_mobilisation"), 2083),
                zone_eligibilite=zone, date_maj=_date(s.get("date_maj"))))
            if len(lot) >= 500:
                _enregistrer(lot)
                lot = []
        _enregistrer(lot)
        trace.services = len(vus)
        if vus:      # un fichier vide (incident) ne vide pas l'annuaire
            trace.retires = ServiceInclusion.objects.exclude(di_id__in=vus).delete()[0]
    except Exception as e:  # noqa: BLE001 — la trace garde l'erreur, l'import ne doit pas casser la page
        log.exception("Import data·inclusion")
        trace.erreur = f"{type(e).__name__} : {e}"[:2000]
    trace.fin = timezone.now()
    trace.save()
    return trace


CHAMPS = ["source", "structure_id", "structure_nom", "structure_siret", "nom", "description", "type", "thematiques",
          "publics", "frais", "modes_accueil", "conditions_acces", "adresse", "code_postal", "commune", "code_insee",
          "latitude", "longitude", "telephone", "courriel", "horaires_accueil", "lien_source", "lien_mobilisation",
          "zone_eligibilite", "date_maj"]


def _enregistrer(lot):
    from .models import ServiceInclusion
    if lot:
        with transaction.atomic():
            ServiceInclusion.objects.bulk_create(lot, update_conflicts=True, unique_fields=["di_id"], update_fields=CHAMPS)


def lancer_en_arriere_plan(user=None):
    """Depuis la page d'état : l'import (quelques minutes) tourne à part, la page se recharge pour suivre."""
    from .models import ImportInclusion
    if ImportInclusion.objects.filter(fin__isnull=True, debut__gte=timezone.now() - timedelta(hours=1)).exists():
        return False

    def travail():
        from django.db import connection
        try:
            importer(user=user)
        finally:
            connection.close()
    threading.Thread(target=travail, daemon=True).start()
    return True


# ----------------------------------------------------------------------------- recherche
def _distance(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2
         + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(h))


def centre_commune(commune, code_postal=""):
    """Point de référence d'une commune calculé à partir des services qui s'y trouvent (pas de géocodage externe)."""
    from django.db.models import Avg, Q

    from .models import ServiceInclusion
    q = Q()
    if commune:
        q |= Q(commune__iexact=commune.strip())
    if code_postal:
        q |= Q(code_postal=code_postal.strip())
    if not q:
        return None
    m = ServiceInclusion.objects.filter(q, latitude__isnull=False).aggregate(la=Avg("latitude"), lo=Avg("longitude"))
    return (m["la"], m["lo"]) if m["la"] is not None else None


def rechercher(categories=(), commune="", code_postal="", gratuit=False, presentiel=False, texte="", limite=60):
    """Services filtrés et triés par distance à la commune (à défaut : même commune d'abord, puis par nom)."""
    from django.db.models import Q

    from .models import ServiceInclusion
    qs = ServiceInclusion.objects.all()
    if texte:
        qs = qs.filter(Q(nom__icontains=texte) | Q(structure_nom__icontains=texte) | Q(description__icontains=texte))
    if gratuit:
        qs = qs.exclude(frais="payant")
    services = list(qs)
    if categories:
        cats = set(categories)
        services = [s for s in services if cats & set(s.categories) or cats & set(s.thematiques or [])]
    if presentiel:
        services = [s for s in services if not s.modes_accueil or "en-presentiel" in s.modes_accueil]
    centre = centre_commune(commune, code_postal)
    for s in services:
        s.distance = (_distance(centre, (s.latitude, s.longitude))
                      if centre and s.latitude is not None and s.longitude is not None else None)
    nom_commune = (commune or "").strip().lower()
    services.sort(key=lambda s: (s.distance if s.distance is not None else
                                 (0 if s.commune.lower() == nom_commune else 9999), s.structure_nom, s.nom))
    return services[:limite], len(services), centre
