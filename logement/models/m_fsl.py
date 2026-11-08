# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/models/m_fsl.py
"""Logement : demandes d'aide au fonds de solidarité pour le logement (FSL).

Générique : le gestionnaire du FSL dépend de la commune (Métropole, Département…), ses formulaires officiels sont
déposés en administration (PDF vierges, jamais dans le dépôt) et CID y écrit les données à leur place, page par page.
Sans formulaire déposé, CID produit une trame générique avec les mêmes rubriques."""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class GestionnaireFSL(models.Model):
    """Qui gère le FSL pour une commune. Paramétré en administration (un département peut en avoir plusieurs)."""
    nom = models.CharField(max_length=150, help_text="Ex. « Métropole … – Service solidarité FSL »")
    adresse = models.TextField(blank=True, help_text="Adresse d'envoi des dossiers")
    codes_postaux = models.TextField(
        blank=True, help_text="Codes postaux couverts, séparés par des virgules ou des retours à la ligne. "
                              "Vide + « par défaut » : toutes les autres communes.")
    par_defaut = models.BooleanField(default=False, help_text="Gestionnaire des communes qui ne sont listées nulle part")
    transmission = models.CharField(
        max_length=200, blank=True,
        help_text="Par où passe le dossier, si la MDS ne l'envoie pas directement (ex. « par le service du "
                  "logement du Département »). Affiché à l'agent au moment de l'envoi.")
    parametres = models.JSONField(
        default=dict, blank=True,
        help_text='Plafonds du règlement intérieur, facultatifs : {"plafond_acces": 2000, '
                  '"plafond_equipement_seul": 500, "plafond_equipement_famille": 900, '
                  '"bareme_equipement": {"table_cuisson": 150, …}}. CID prévient, il ne bloque pas.')
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Gestionnaire du FSL"
        verbose_name_plural = "Gestionnaires du FSL"
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def liste_codes_postaux(self):
        import re
        return [c for c in re.split(r'[\s,;]+', self.codes_postaux or '') if c]

    @classmethod
    def pour_code_postal(cls, code_postal):
        actifs = cls.objects.filter(actif=True)
        for g in actifs:
            if code_postal and code_postal in g.liste_codes_postaux():
                return g
        return actifs.filter(par_defaut=True).first()


class FormulaireOfficiel(models.Model):
    """PDF vierge d'un gestionnaire, déposé en administration. Stocké en base (pas sur le disque du serveur)."""
    FORMULAIRE_ACCES, AVIS_MOTIVE, ARGUMENTAIRE = 'FSL_ACCES', 'FSL_AVIS', 'FSL_ARGUMENTAIRE'
    CONTRAT_PRET, CONTRAT_GARANTIE, PRELEVEMENT = 'FSL_PRET', 'FSL_GARANTIE', 'FSL_PRELEVEMENT'
    CONVENTION_ACCES, IDENTIFICATION_LOGEMENT = 'FSL_CONVENTION', 'FSL_IDENT_LOGEMENT'
    LISTE_PIECES, VERSEMENT_DIRECT_AL = 'FSL_PIECES', 'CERFA_11362'
    FORMULAIRE_EAU, FORMULAIRE_ENERGIE = 'FSL_EAU', 'FSL_ENERGIE'
    AVIS_FLUIDES, ARGUMENTAIRE_FLUIDES = 'FSL_AVIS_FLUIDES', 'FSL_ARGU_FLUIDES'
    FORMULAIRE_MAINTIEN, ARGUMENTAIRE_MAINTIEN = 'FSL_MAINTIEN', 'FSL_ARGU_MAINTIEN'
    COPP_FICHE_1, COPP_FICHE_2 = 'COPP_FICHE_1', 'COPP_FICHE_2'
    ENGAGEMENTS, CONVENTION_CONCORDAT, LISTE_PIECES_MAINTIEN = 'FSL_ENGAGEMENTS', 'FSL_CONCORDAT', 'FSL_PIECES_MAINTIEN'
    EXP_DSF, EXP_QUESTIONNAIRE, EXP_CARENCE = 'EXP_DSF', 'EXP_QUEST_BAILLEUR', 'EXP_CARENCE'
    CODES = [
        (FORMULAIRE_ACCES, "Demande d'aide à l'accès au logement"),
        (AVIS_MOTIVE, "Avis motivé et proposition du travailleur social"),
        (ARGUMENTAIRE, "Argumentaire de pièces manquantes (note du cadre)"),
        (CONTRAT_PRET, "Contrat de prêt"),
        (CONTRAT_GARANTIE, "Contrat de mise en jeu de la garantie"),
        (PRELEVEMENT, "Autorisation de prélèvement"),
        (CONVENTION_ACCES, "Convention d'accès au logement"),
        (IDENTIFICATION_LOGEMENT, "Fiche d'identification du logement (bailleur privé)"),
        (LISTE_PIECES, "Liste des pièces à fournir"),
        (VERSEMENT_DIRECT_AL, "Demande de versement direct de l'allocation de logement (Cerfa 11362)"),
        (FORMULAIRE_EAU, "Demande d'aide aux impayés d'eau"),
        (FORMULAIRE_ENERGIE, "Demande d'aide aux impayés d'électricité, de gaz"),
        (AVIS_FLUIDES, "Avis motivé du travailleur social (énergie, eau)"),
        (ARGUMENTAIRE_FLUIDES, "Argumentaire de pièces manquantes, énergie et eau (note du cadre)"),
        (FORMULAIRE_MAINTIEN, "Demande FSL maintien ou concordat"),
        (ARGUMENTAIRE_MAINTIEN, "Argumentaire de pièces manquantes, maintien et concordat (note du cadre)"),
        (ENGAGEMENTS, "Engagements du locataire et du bailleur"),
        (CONVENTION_CONCORDAT, "Concordat – convention de résorption de dette locative"),
        (LISTE_PIECES_MAINTIEN, "Liste des pièces à fournir (maintien)"),
        (COPP_FICHE_1, "Commission publics prioritaires (COPP) – fiche de saisine, page 1"),
        (COPP_FICHE_2, "Commission publics prioritaires (COPP) – fiche de saisine, page 2"),
        (EXP_DSF, "Expulsions – diagnostic social et financier (Cerfa 16227) : remplace celui livré avec CID"),
        (EXP_QUESTIONNAIRE, "Expulsions – questionnaire bailleur pour le DSF"),
        (EXP_CARENCE, "Expulsions – bordereau de carence"),
    ]
    gestionnaire = models.ForeignKey(GestionnaireFSL, on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='formulaires',
                                     help_text="Vide : vaut pour tous les gestionnaires (Cerfa national, document MDS)")
    code = models.CharField(max_length=20, choices=CODES)
    version = models.CharField(max_length=30, blank=True, help_text="Ex. « 03/2025 »")
    nom_fichier = models.CharField(max_length=200, blank=True, editable=False)
    contenu = models.BinaryField(editable=False)
    reglages = models.JSONField(
        default=dict, blank=True,
        help_text="Corrections de placement, si un champ tombe mal : {\"cle\": {\"dx\": 3, \"dy\": -2}} "
                  "ou {\"cle\": {\"page\": 0, \"x\": 120, \"y\": 400}}. La clé figure dans l'aperçu.")
    actif = models.BooleanField(default=True)
    date_depot = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Formulaire officiel (PDF vierge)"
        verbose_name_plural = "Formulaires officiels (PDF vierges)"
        ordering = ['gestionnaire__nom', 'code']

    def __str__(self):
        return f"{self.get_code_display()} – {self.gestionnaire or 'tous'}{f' ({self.version})' if self.version else ''}"

    @classmethod
    def pour(cls, code, gestionnaire):
        qs = cls.objects.filter(code=code, actif=True).exclude(contenu=b'')
        return qs.filter(gestionnaire=gestionnaire).first() or qs.filter(gestionnaire__isnull=True).first()


class DemandeFSL(models.Model):
    ACCES, EAU, ENERGIE, MAINTIEN = 'ACCES', 'EAU', 'ENERGIE', 'MAINTIEN'
    TYPES = [(ACCES, "Accès au logement"), (MAINTIEN, "Maintien dans le logement (ou concordat)"),
             (EAU, "Impayés d'eau"), (ENERGIE, "Impayés d'électricité, de gaz")]
    FLUIDES = {EAU, ENERGIE}
    BROUILLON, A_VALIDER, VALIDEE = 'BROUILLON', 'A_VALIDER_CADRE', 'VALIDEE_CADRE'
    ENVOYEE, AJOURNEE, ACCORDEE, REFUSEE, ABANDONNEE = 'ENVOYEE', 'AJOURNEE', 'ACCORDEE', 'REFUSEE', 'ABANDONNEE'
    STATUTS = [
        (BROUILLON, "En préparation"),
        (A_VALIDER, "Visa du cadre demandé"),
        (VALIDEE, "Visée par le cadre : prête à envoyer"),
        (ENVOYEE, "Envoyée au FSL"),
        (AJOURNEE, "Ajournée (pièces demandées)"),
        (ACCORDEE, "Accordée"),
        (REFUSEE, "Refusée"),
        (ABANDONNEE, "Abandonnée"),
    ]
    MODIFIABLES = {BROUILLON, VALIDEE, AJOURNEE}
    AVIS = [('FAVORABLE', "Favorable"), ('RESERVE', "Réservé"), ('DEFAVORABLE', "Défavorable")]

    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE, related_name='demandes_fsl')
    mds = models.ForeignKey('mds.MDS', on_delete=models.PROTECT, related_name='demandes_fsl')
    gestionnaire = models.ForeignKey(GestionnaireFSL, on_delete=models.PROTECT, null=True, blank=True,
                                     related_name='demandes')
    type_aide = models.CharField(max_length=10, choices=TYPES, default=ACCES)
    statut = models.CharField(max_length=20, choices=STATUTS, default=BROUILLON)
    # Toutes les rubriques du formulaire (préremplies par CID, corrigées par l'agent)
    donnees = models.JSONField(default=dict, blank=True)
    pieces = models.JSONField(default=dict, blank=True, help_text="{code: 'FOURNIE' | 'MANQUANTE' | 'SANS_OBJET'}")
    avis = models.CharField(max_length=12, choices=AVIS, blank=True)
    instruction_administrative = models.BooleanField(
        "Instruite par un agent administratif", default=False,
        help_text="Énergie, eau : factures de moins de 500 €, sans avis motivé d'un travailleur social.")
    avis_motive = models.TextField("Avis motivé", blank=True)
    proposition_pret = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    proposition_subvention = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    # Cadre (pièces manquantes)
    note_cadre = models.TextField("Note explicative du cadre (pièces manquantes)", blank=True)
    cadre = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='fsl_valides')
    date_validation_cadre = models.DateTimeField(null=True, blank=True)
    # Envoi et réponse du FSL
    date_envoi = models.DateField(null=True, blank=True)
    date_decision = models.DateField(null=True, blank=True)
    montant_accorde_pret = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    montant_accorde_subvention = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    garantie_accordee = models.CharField(max_length=60, blank=True)
    commentaire_decision = models.TextField(blank=True)
    historique = models.JSONField(default=list, blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name='fsl_crees')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Demande FSL"
        verbose_name_plural = "Demandes FSL"
        ordering = ['-date_creation']

    def __str__(self):
        return f"FSL {self.get_type_aide_display().lower()} – {self.beneficiaire} ({self.get_statut_display()})"

    @property
    def est_fluides(self):
        return self.type_aide in self.FLUIDES

    @property
    def montant_dette(self):
        """Énergie, eau : montant de la facture ou des dettes d'électricité et de gaz."""
        from ..services.fsl import d
        dn = self.donnees or {}
        if self.type_aide == self.EAU:
            return d(dn.get('montant_facture'))
        if self.type_aide == self.ENERGIE:
            return d(dn.get('dette_electricite')) + d(dn.get('dette_gaz'))
        if self.type_aide == self.MAINTIEN:
            return d(dn.get('montant_dette'))
        return d(0)

    @property
    def est_concordat(self):
        return self.type_aide == self.MAINTIEN and (self.donnees or {}).get('variante') == 'CONCORDAT'

    @property
    def modifiable(self):
        return self.statut in self.MODIFIABLES

    @property
    def pieces_manquantes(self):
        return [c for c, etat in (self.pieces or {}).items() if etat == 'MANQUANTE']

    @property
    def total_propose(self):
        if self.type_aide != self.ACCES:
            return (self.proposition_pret or Decimal(0)) + (self.proposition_subvention or Decimal(0))
        p = (self.donnees or {}).get('proposition', {})
        total = Decimal(0)
        for v in p.values():
            try:
                total += Decimal(str(v or 0).replace(',', '.'))
            except Exception:
                pass
        return total

    def tracer(self, user, action, detail=""):
        nom = (user.get_full_name() or user.username) if user else "CID"
        self.historique = list(self.historique or []) + [
            {'date': timezone.localtime().strftime('%d/%m/%Y %H:%M'), 'qui': nom, 'action': action, 'detail': detail}]
