from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from mds.models import MDS, UserMDSProfile, MDSReception
from beneficiaire.models import Beneficiaire, LienFamilial
from datetime import date, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = "Initialisation des données de test (agents, familles, salles)"

    def handle(self, *args, **options):
        self.stdout.write("🚀 Création des données de test")

        # ==========================================================
        # 1. Récupération de la MDS de test
        # ==========================================================
        mds, _ = MDS.objects.get_or_create(
            code_mds="MDSTEST1",
            defaults={
                "nom": "MDS TEST 01",
                "adresse": "12 rue des Amandiers",
                "code_postal": "13110",
                "ville": "Port-de-Bouc",
                "telephone": "0491450000",
                "email": "mds.test@example.com",
                "active": True,
                "date_ouverture": timezone.now().date(),
            }
        )
        self.stdout.write(f"✅ MDS : {mds.code_mds} - {mds.nom}")

        # ==========================================================
        # 2. Création des salles
        # ==========================================================
        salles_data = [
            {"nom": "Salle Permanence A", "capacite": 3, "type": "BUREAU"},
            {"nom": "Salle Permanence B", "capacite": 3, "type": "BUREAU"},
            {"nom": "Salle Permanence C", "capacite": 3, "type": "BUREAU"},
            {"nom": "Salle Permanence D (grande)", "capacite": 6, "type": "BUREAU"},
            {"nom": "Salle Réunion", "capacite": 19, "type": "REUNION"},
            {"nom": "CCAS de Saint-Mitre", "capacite": 2, "type": "EXTERNE", "est_externe": True},
            {"nom": "École Jean Jaurès", "capacite": 4, "type": "EXTERNE", "est_externe": True},
        ]

        salles = []
        for s in salles_data:
            salle, created = MDSReception.objects.get_or_create(
                mds=mds,
                nom=s["nom"],
                defaults={
                    "capacite": s["capacite"],
                    "type_salle": s["type"],
                    "actif": True,
                    "est_externe": s.get("est_externe", False),
                    "horaire_debut": time(9, 0),
                    "horaire_fin": time(17, 0),
                    "disponible_lundi": True,
                    "disponible_mardi": True,
                    "disponible_mercredi": True,
                    "disponible_jeudi": True,
                    "disponible_vendredi": True,
                }
            )
            salles.append(salle)
            self.stdout.write(f"   {'✅ Créée' if created else '📌 Existe'} : {salle.nom} (cap. {salle.capacite})")

        # ==========================================================
        # 3. Création des utilisateurs (agents)
        # ==========================================================
        profils = {
            "agent_social": "MDS_AGENTS_SOCIAUX",
            "agent_administratif": "MDS_ADMINISTRATIFS",
            "cadre": "MDS_CADRES",
        }

        agents_data = [
            ("asmith", "Agent Social 1", "agent_social", False),
            ("bjones", "Agent Social 2", "agent_social", False),
            ("cdubois", "Agent Social 3", "agent_social", False),
            ("dmorel", "Agent Social 4", "agent_social", False),
            ("elambert", "Agent Social 5", "agent_social", False),
            ("fbernard", "Agent Social 6", "agent_social", False),
            ("garnaud", "Agent Social 7", "agent_social", False),
            ("hadmin", "Agent Admin 1", "agent_administratif", False),
            ("iadm2", "Agent Admin 2", "agent_administratif", False),
            ("jcadre1", "Cadre MDS 1", "cadre", False),
            ("kchef", "Chef de service (propriétaire)", "cadre", True),
        ]

        for username, fullname, profil_key, est_proprietaire in agents_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": fullname.split()[0],
                    "last_name": fullname.split()[-1],
                    "email": f"{username}@test.fr",
                    "is_active": True,
                }
            )
            if created:
                user.set_password("testpass123")
                user.save()

            profil = profils[profil_key]
            profile, _ = UserMDSProfile.objects.get_or_create(
                user=user,
                mds=mds,
                defaults={
                    "principale": True,
                    "actif": True,
                    "peut_gerer_utilisateurs": est_proprietaire,
                    "role_specifique": "Chef de service" if est_proprietaire else "",
                }
            )
            self.stdout.write(f"   {'✅ Créé' if created else '📌 Existe'} : {username} ({fullname}) – {profil}")

        # ==========================================================
        # 4. Création des bénéficiaires (familles)
        # ==========================================================
        def create_beneficiaire(nom, prenom, role, mds, code_interne_prefix):
            code = f"{code_interne_prefix}-{prenom[:3].upper()}"
            benef, created = Beneficiaire.objects.get_or_create(
                code_interne=code,
                defaults={
                    "nom": nom.upper(),
                    "prenom": prenom,
                    "civilite": "M." if role == "pere" else "MME",
                    "date_naissance": date.today() - timedelta(days=365 * 30),
                    "adresse": "1 rue de la MDS",
                    "code_postal": "13110",
                    "ville": "Port-de-Bouc",
                    "mds": mds,
                    "statut": "ACTIF",
                }
            )
            if created:
                self.stdout.write(f"   ✅ {prenom} {nom.upper()} ({code})")
            return benef

        # Famille 1 : monoparentale (père + 2 enfants)
        pere = create_beneficiaire("MONOP", "Jean", "pere", mds, "FAM1")
        enfant1 = create_beneficiaire("MONOP", "Lucas", "enfant", mds, "FAM1")
        enfant2 = create_beneficiaire("MONOP", "Emma", "enfant", mds, "FAM1")

        LienFamilial.objects.get_or_create(personne_a=pere, personne_b=enfant1, type_lien="ENFANT", defaults={"vit_au_foyer": True})
        LienFamilial.objects.get_or_create(personne_a=pere, personne_b=enfant2, type_lien="ENFANT", defaults={"vit_au_foyer": True})

        # Famille 2 : recomposée
        pere2 = create_beneficiaire("RECOMP", "Paul", "pere", mds, "FAM2")
        mere2 = create_beneficiaire("RECOMP", "Sophie", "mere", mds, "FAM2")
        enfant_paul1 = create_beneficiaire("RECOMP", "Tom", "enfant", mds, "FAM2")
        enfant_paul2 = create_beneficiaire("RECOMP", "Lea", "enfant", mds, "FAM2")
        enfant_commun = create_beneficiaire("RECOMP", "Leo", "enfant", mds, "FAM2")
        nouvelle_compagne = create_beneficiaire("RECOMP", "Julie", "conjointe", mds, "FAM2")

        LienFamilial.objects.get_or_create(personne_a=pere2, personne_b=enfant_paul1, type_lien="ENFANT", defaults={"vit_au_foyer": False})
        LienFamilial.objects.get_or_create(personne_a=pere2, personne_b=enfant_paul2, type_lien="ENFANT", defaults={"vit_au_foyer": False})
        LienFamilial.objects.get_or_create(personne_a=mere2, personne_b=enfant_paul1, type_lien="ENFANT", defaults={"vit_au_foyer": True})
        LienFamilial.objects.get_or_create(personne_a=mere2, personne_b=enfant_paul2, type_lien="ENFANT", defaults={"vit_au_foyer": True})
        LienFamilial.objects.get_or_create(personne_a=pere2, personne_b=nouvelle_compagne, type_lien="CONJOINT", defaults={"vit_au_foyer": True})
        LienFamilial.objects.get_or_create(personne_a=pere2, personne_b=enfant_commun, type_lien="ENFANT", defaults={"vit_au_foyer": True})

        # Famille 3 : classique avec 3 enfants dont 1 de -5 ans
        pere3 = create_beneficiaire("CLASSIC", "Marc", "pere", mds, "FAM3")
        mere3 = create_beneficiaire("CLASSIC", "Claire", "mere", mds, "FAM3")
        enfant3a = create_beneficiaire("CLASSIC", "Hugo", "enfant", mds, "FAM3")
        enfant3b = create_beneficiaire("CLASSIC", "Chloe", "enfant", mds, "FAM3")
        enfant3c = create_beneficiaire("CLASSIC", "Louis", "enfant", mds, "FAM3")
        enfant3c.date_naissance = date.today() - timedelta(days=365 * 4)
        enfant3c.save()

        LienFamilial.objects.get_or_create(personne_a=pere3, personne_b=enfant3a, type_lien="ENFANT", defaults={"vit_au_foyer": True})
        LienFamilial.objects.get_or_create(personne_a=pere3, personne_b=enfant3b, type_lien="ENFANT", defaults={"vit_au_foyer": True})
        LienFamilial.objects.get_or_create(personne_a=pere3, personne_b=enfant3c, type_lien="ENFANT", defaults={"vit_au_foyer": True})
        LienFamilial.objects.get_or_create(personne_a=mere3, personne_b=enfant3a, type_lien="ENFANT", defaults={"vit_au_foyer": True})
        LienFamilial.objects.get_or_create(personne_a=mere3, personne_b=enfant3b, type_lien="ENFANT", defaults={"vit_au_foyer": True})
        LienFamilial.objects.get_or_create(personne_a=mere3, personne_b=enfant3c, type_lien="ENFANT", defaults={"vit_au_foyer": True})
        LienFamilial.objects.get_or_create(personne_a=pere3, personne_b=mere3, type_lien="CONJOINT", defaults={"vit_au_foyer": True})

        self.stdout.write(self.style.SUCCESS("\n🎉 Données de test créées avec succès"))
