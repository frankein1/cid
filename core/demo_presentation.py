# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/demo_presentation.py
"""
Jeu de démonstration « présentation » : 30 familles fictives (codes PRES…), réparties sur les deux MDS de test, avec
un an d'entretiens, des budgets du foyer et des participations aux ateliers, pour que les statistiques de
l'accompagnement aient des effectifs supérieurs au secret statistique.
Tout est inventé et tiré au sort avec une graine fixe (le même jeu à chaque réinitialisation). Appelé par init_demo.
"""
import random
from datetime import date, time, timedelta

GRAINE = 13
MARQUE = "Séance de démonstration"
NOMS = ["ARNAUD", "BARRE", "BENALI", "BLANC", "BONNET", "BOUZID", "CARON", "CHEVALIER", "COLIN", "DIALLO", "DUMAS",
        "FAURE", "FONTAINE", "GAUTIER", "GIRARD", "HADDAD", "JOLY", "KHELIFI", "LACROIX", "LAMBERT", "LEMAIRE", "MANSOURI",
        "MARCHAND", "MERCIER", "MOREL", "NGUYEN", "PERRIN", "PICARD", "RENARD", "ROCHE", "SANCHEZ", "VIDAL"]
PRENOMS_F = ["Amina", "Nadia", "Sandrine", "Karima", "Julie", "Laura", "Sonia", "Fatima", "Audrey", "Samia", "Élodie",
             "Myriam", "Hélène", "Aïcha", "Vanessa", "Stéphanie", "Linda", "Yasmina", "Nathalie", "Sabrina"]
PRENOMS_M = ["Karim", "Mehdi", "Julien", "Sébastien", "Nicolas", "David", "Rachid", "Thomas", "Kevin", "Anthony",
             "Mohamed", "Christophe", "Yannick", "Bruno", "Farid", "Olivier"]
PRENOMS_ENFANTS = ["Lina", "Adam", "Inaya", "Noah", "Jade", "Rayan", "Lou", "Ibrahim", "Mila", "Nolan", "Ambre",
                   "Ilyes", "Zoé", "Gabin", "Sofia", "Yanis", "Lya", "Sacha", "Maël", "Romane"]
COMMUNES = {1: [("13110", "Port-de-Bouc")] * 3 + [("13270", "Fos-sur-Mer"), ("13920", "Saint-Mitre-les-Remparts")],
            2: [("13500", "Martigues")] * 3 + [("13117", "Lavéra"), ("13730", "Saint-Victoret")]}
RUES = ["rue des Lilas", "avenue de la Mer", "chemin des Vignes", "rue du Stade", "impasse des Mouettes",
        "boulevard des Salins", "allée des Platanes", "rue de la Gare"]
PARTENAIRES = [("Point conseil budget (fictif)", "BUDGET"), ("Épicerie solidaire (fictif)", "AUTRE"),
               ("Mission locale (fictif)", "EMPLOI"), ("Centre communal d'action sociale (fictif)", "ACCES_DROITS"),
               ("Association d'aide aux victimes (fictif)", "JUSTICE")]
CREANCIERS = ["Fournisseur d'énergie (fictif)", "Bailleur (fictif)", "Organisme de crédit (fictif)",
              "Opérateur téléphonique (fictif)"]
# profils de foyer : (libellé, adultes, enfants min-max, âge min-max du référent, poids)
PROFILS = [("monoparentale", 1, (1, 3), (22, 48), 9), ("couple_enfants", 2, (1, 4), (25, 50), 7),
           ("couple", 2, (0, 0), (25, 65), 3), ("seul", 1, (0, 0), (19, 59), 7), ("senior", 1, (0, 0), (62, 84), 4)]
MODES = [("RDV", 45, (40, 75)), ("ACCUEIL", 14, (15, 30)), ("TELEPHONE", 20, (10, 25)), ("VAD", 12, (45, 90)),
         ("ECRIT", 6, (10, 20)), ("EXTERIEUR", 3, (60, 120))]
OBJETS = {"rsa": "Suivi du contrat RSA", "budget": "Point budget", "logement": "Logement", "acces-droits": "Ouverture de droits",
          "emploi": "Recherche d'emploi", "parentalite": "Parentalité", "sante": "Accès aux soins",
          "autonomie": "Maintien à domicile", "urgence": "Demande d'aide d'urgence", "mobilite": "Mobilité",
          "demarches": "Démarches en ligne", "vif": "Mise en sécurité", "protection-enfance": "Suivi de mesure",
          "masp": "Suivi MASP"}


def _choix_pondere(r, items, poids):
    return r.choices(items, weights=poids, k=1)[0]


def creer(cmd):
    """cmd : la commande init_demo (pour self.j, self.mds1, self.mds2, comptes, stdout)."""
    from beneficiaire.models import (Beneficiaire, BudgetFoyer, EntretienSocial, LienFamilial,
                                     TypeAccompagnement)
    from core.models import User
    from partenaires.models import Partenaire
    from planning.models import Atelier, ParticipantAtelier as P, SeanceAtelier

    r = random.Random(GRAINE)
    j = cmd.j
    Beneficiaire.tous.filter(code_interne__startswith="PRES").delete()
    SeanceAtelier.objects.filter(description__startswith=MARQUE).delete()
    partenaires = [Partenaire.objects.get_or_create(organisme=o, defaults={"thematique": t})[0] for o, t in PARTENAIRES]
    partenaires += list(Partenaire.objects.exclude(organisme__in=[o for o, _ in PARTENAIRES]))
    types = {t.code: t for t in TypeAccompagnement.objects.all()}
    agents = {1: [User.objects.get(username=u) for u in ("as1_mds1", "as2_mds1", "as3_mds1")],
              2: [User.objects.get(username="as1_mds2")]}
    mds = {1: cmd.mds1, 2: cmd.mds2}
    debut_annee = date(j.year, 1, 1)
    noms = r.sample(NOMS, len(NOMS))
    foyers = []
    nb_ent = nb_bud = 0
    for n in range(30):
        num_mds = 1 if n < 20 else 2
        profil, nb_adultes, (emin, emax), (amin, amax), _ = _choix_pondere(r, PROFILS, [p[4] for p in PROFILS])
        cp, ville = r.choice(COMMUNES[num_mds])
        adresse = f"{r.randint(1, 60)} {r.choice(RUES)}"
        nom = noms[n % len(noms)]
        age = r.randint(amin, amax)
        femme = profil == "monoparentale" or r.random() < 0.6
        statut = {"monoparentale": r.choice(["CELIBATAIRE", "DIVORCE", "SEPARE"]), "couple_enfants": r.choice(["MARIE", "CONCUBINAGE", "PACSE"]),
                  "couple": r.choice(["MARIE", "CONCUBINAGE"]), "seul": r.choice(["CELIBATAIRE", "DIVORCE"]),
                  "senior": r.choice(["VEUF", "DIVORCE", "CELIBATAIRE"])}[profil]

        def personne(suffixe, civ, prenom, age_p, statut_m="CELIBATAIRE"):
            naissance = j - timedelta(days=int(age_p * 365.25) + r.randint(0, 300))
            return Beneficiaire.tous.create(
                code_interne=f"PRES{n + 1:02d}-{suffixe}", civilite=civ, nom=nom, prenom=prenom, date_naissance=naissance,
                adresse=adresse, code_postal=cp, ville=ville, mds=mds[num_mds], statut="ACTIF", marital_status=statut_m,
                cree_par=agents[num_mds][0])
        ref = personne("A", "MME" if femme else "M.", r.choice(PRENOMS_F if femme else PRENOMS_M), age, statut)
        membres = []
        if nb_adultes == 2:
            conj = personne("B", "M." if femme else "MME", r.choice(PRENOMS_M if femme else PRENOMS_F),
                            max(19, age + r.randint(-5, 6)), statut)
            membres.append(conj)
            for a, b in ((ref, conj), (conj, ref)):
                LienFamilial.objects.create(personne_a=a, personne_b=b, type_lien="CONJOINT", vit_au_foyer=True, date_debut=j)
        enfants = []
        for k in range(r.randint(emin, emax)):
            e = personne(f"E{k + 1}", r.choice(["M.", "MME"]), r.choice(PRENOMS_ENFANTS), r.randint(0, min(17, max(0, age - 18))))
            enfants.append(e)
            for parent in [ref] + membres:
                LienFamilial.objects.create(personne_a=parent, personne_b=e, type_lien="ENFANT", vit_au_foyer=True,
                                            est_responsable_legal=True, date_debut=j)
                LienFamilial.objects.create(personne_a=e, personne_b=parent, type_lien="PARENT", vit_au_foyer=True, date_debut=j)
        taille = 1 + len(membres) + len(enfants)
        foyers.append((ref, num_mds, profil, taille))

        # --- motifs d'accompagnement du foyer
        rsa = profil in ("monoparentale", "seul", "couple_enfants") and r.random() < 0.55
        motifs = ["acces-droits", "budget", "logement"]
        motifs += ["rsa", "emploi"] if rsa else (["emploi"] if profil != "senior" else [])
        motifs += ["parentalite"] if enfants else []
        motifs += ["autonomie", "sante"] if profil == "senior" else (["sante"] if r.random() < 0.3 else [])
        motifs += ["urgence"] if r.random() < 0.3 else []
        motifs += ["mobilite"] if r.random() < 0.2 else []
        motifs += ["demarches"] if r.random() < 0.35 else []
        if n in (4, 17):
            motifs.append("vif")
        if n in (6, 22) and enfants:
            motifs.append("protection-enfance")
        if n == 11:
            motifs.append("masp")

        # --- entretiens : un an glissant, quelques-uns l'an dernier (personnes déjà connues)
        dates = sorted(debut_annee + timedelta(days=r.randint(0, max(1, (j - debut_annee).days)))
                       for _ in range(r.randint(1, 7)))
        if r.random() < 0.35:
            dates = [debut_annee - timedelta(days=r.randint(20, 300))] + dates
        for d in dates:
            mode, _, (dmin, dmax) = _choix_pondere(r, MODES, [m[1] for m in MODES])
            choisis = r.sample(motifs, k=min(len(motifs), r.choice([1, 1, 2])))
            legal = [m for m in ("rsa", "protection-enfance", "masp") if m in motifs]
            if legal and r.random() < 0.6 and legal[0] not in choisis:
                choisis = [legal[0]] + choisis[:1]          # les accompagnements légaux reviennent à chaque rencontre
            suite = r.random() < 0.35
            echeance = d + timedelta(days=r.randint(7, 30)) if suite else None
            e = EntretienSocial.objects.create(
                beneficiaire=ref, date=d, heure=time(r.choice([9, 10, 11, 14, 15, 16])), mode=mode,
                duree_minutes=r.randint(dmin, dmax) // 5 * 5, auteur=r.choice(agents[num_mds]), objet=OBJETS[choisis[0]],
                synthese="Entretien fictif de démonstration.",
                suite_a_donner="Relance fictive à faire" if suite else "", echeance=echeance,
                suite_faite=bool(suite and echeance < j - timedelta(days=10) and r.random() < 0.8),
                orientation=r.choice(partenaires) if r.random() < 0.22 else None)
            e.cree_par = e.auteur
            e.save(update_fields=["cree_par"])
            e.types.set([types[c] for c in choisis if c in types])
            if membres and r.random() < 0.3:
                e.personnes_presentes.set(membres)
            nb_ent += 1

        # --- budget du foyer (8 foyers sur 10), parfois deux budgets successifs
        if r.random() < 0.8:
            for k in range(1 if r.random() < 0.7 else 2):
                res = {}
                if rsa:
                    res["rsa"] = 635 if taille == 1 else 635 + 190 * (taille - 1)
                if profil == "senior":
                    res["retraite"] = r.choice([1012, 1100, 1250])
                elif not rsa:
                    res["salaire"] = r.randint(750, 1450)
                    if nb_adultes == 2 and r.random() < 0.5:
                        res["chomage"] = r.randint(600, 1100)
                if r.random() < 0.12:
                    res["aah"] = 1016
                if len(enfants) >= 2:
                    res["familiales"] = 148 if len(enfants) == 2 else 338
                res["logement"] = r.randint(120, 380)
                loyer = r.randint(480, 860)
                elec = r.randint(45, 130)
                ch = {"loyer": [loyer, 0], "electricite": [elec, 0], "telephone": [r.randint(20, 60), 0],
                      "assurance_habitation": [r.randint(12, 30), 0]}
                if r.random() < 0.3:
                    ch["credits"] = [r.randint(80, 320), 0]
                if enfants and r.random() < 0.5:
                    ch["garde_scolarite"] = [r.randint(30, 150), 0]
                impaye = r.random() < 0.35
                if impaye:
                    poste = r.choice(["electricite", "electricite", "loyer", "telephone"])
                    ch[poste] = [0 if r.random() < 0.4 else ch[poste][0], ch[poste][0] * r.randint(1, 3)]
                dettes = []
                if impaye or r.random() < 0.15:
                    dettes = [{"creancier": r.choice(CREANCIERS), "montant": str(r.randint(150, 2500))}]
                BudgetFoyer.objects.create(
                    beneficiaire=ref, date_etabli=max(debut_annee, j - timedelta(days=r.randint(5, 290))) if k == 0 else j - timedelta(days=r.randint(1, 30)),
                    nb_personnes_foyer=taille, cree_par=agents[num_mds][0],
                    ressources={"v": 2, "lignes": {c: {"demandeur": str(v), "conjoint": "0", "autres": "0"} for c, v in res.items()}, "precisions": {}},
                    charges={"v": 2, "lignes": {c: {"payee": str(p), "non_payee": str(np_)} for c, (p, np_) in ch.items()}, "precisions": {}},
                    dettes=dettes)
                nb_bud += 1

    # --- ateliers : séances passées de l'année, participants pris dans les foyers de la MDS
    ateliers = {1: list(Atelier.objects.filter(nom__in=["Gérer son budget au quotidien", "Cuisine à petit prix",
                                                         "Premiers pas numériques"])),
                2: [Atelier.objects.get_or_create(nom="Bouger sans voiture", mds=cmd.mds2,
                                                  defaults={"description": "Atelier fictif de démonstration."})[0],
                    Atelier.objects.filter(nom="Gérer son budget au quotidien").first()]}
    nb_seances = 0
    for num_mds, liste in ateliers.items():
        gens = [f[0] for f in foyers if f[1] == num_mds]
        jour = debut_annee + timedelta(days=10)
        while jour < j - timedelta(days=3):
            if jour.weekday() < 5:
                at = liste[nb_seances % len(liste)]
                places = r.choice([6, 8, 10, None])
                s = SeanceAtelier.objects.create(atelier=at, mds=mds[num_mds], date=jour, heure_debut=time(14),
                                                 heure_fin=time(16), lieu="Salle polyvalente de la MDS", places=places,
                                                 description=f"{MARQUE} (fictive).", cree_par=agents[num_mds][0])
                nb_seances += 1
                demande = r.randint(3, (places or 9) + 3)
                for k, b in enumerate(r.sample(gens, k=min(len(gens), demande))):
                    attente = places is not None and k >= places
                    P.objects.create(seance=s, beneficiaire=b, liste=P.ATTENTE if attente else P.PRINCIPALE,
                                     presence="" if attente else _choix_pondere(r, [P.VENU, P.ABSENT, P.EXCUSE], [78, 12, 10]))
                if r.random() < 0.4:
                    P.objects.create(seance=s, type=P.EXTERNE, prenom=r.choice(PRENOMS_F), nom=r.choice(NOMS),
                                     ville=COMMUNES[num_mds][0][1], presence=P.VENU)
            jour += timedelta(days=r.randint(18, 30))
    cmd.stdout.write(f"✅ Présentation : {len(foyers)} familles fictives, {nb_ent} entretiens, {nb_bud} budgets, "
                     f"{nb_seances} séances d'ateliers")
