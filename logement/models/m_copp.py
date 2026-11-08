# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# logement/models/m_copp.py
from django.conf import settings
from django.db import models
from django.utils import timezone


from .m_fsl import DemandeFSL


# ==========================================================================
# COMMISSION DES PUBLICS PRIORITAIRES (COPP / CTPP)
# ==========================================================================

class CommissionPublicsPrioritaires(models.Model):
    """Séance de la commission (dispositif local, paramétré en administration ; un autre département peut ne pas
    l'utiliser ou lui donner un autre nom)."""
    nom = models.CharField(max_length=150, default="Commission territoriale des publics prioritaires")
    territoire = models.CharField(max_length=150, blank=True, help_text="Ex. « Pays de Martigues »")
    mds = models.ManyToManyField('mds.MDS', blank=True, related_name='commissions_copp',
                                 help_text="MDS qui présentent des dossiers à cette séance")
    date = models.DateField("Date de la commission")
    date_limite_depot = models.DateField("Date limite de dépôt des dossiers")
    lieu = models.CharField(max_length=200, blank=True)
    horaire = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "Commission des publics prioritaires (séance)"
        verbose_name_plural = "Commissions des publics prioritaires (séances)"
        ordering = ['date']

    def __str__(self):
        return f"{self.nom} – {self.date:%d/%m/%Y}" + (f" ({self.territoire})" if self.territoire else "")

    @classmethod
    def prochaine(cls, mds):
        j = timezone.localdate()
        return cls.objects.filter(mds=mds, date_limite_depot__gte=j).order_by('date_limite_depot').first()


class SaisineCOPP(models.Model):
    BROUILLON, ENVOYEE, EXAMINEE, ABANDONNEE = 'BROUILLON', 'ENVOYEE', 'EXAMINEE', 'ABANDONNEE'
    STATUTS = [(BROUILLON, "En préparation"), (ENVOYEE, "Envoyée à la commission"),
               (EXAMINEE, "Examinée en commission"), (ABANDONNEE, "Abandonnée")]
    # Plusieurs motifs possibles ; « autre » à préciser (pour les statistiques, la liste reste ouverte)
    MOTIFS = [
        ('DALO_ANCIEN', "Demande ou DALO sans décision, délai anormalement long"),
        ('DALO_REFUSE', "DALO refusé"),
        ('EXPULSION', "Expulsion ou procédure d'expulsion"),
        ('SANS_LOGEMENT', "Sans logement, hébergé(e) chez des tiers ou en structure"),
        ('SURNOMBRE', "Sur-occupation du logement"),
        ('INDIGNE', "Logement insalubre, indigne ou indécent"),
        ('INADAPTE', "Logement inadapté à la composition familiale"),
        ('HANDICAP', "Handicap, perte d'autonomie ou problème de santé"),
        ('VIOLENCES', "Violences intrafamiliales, insécurité"),
        ('COUT', "Logement trop cher (taux d'effort)"),
        ('SEPARATION', "Séparation, rupture familiale"),
        ('AUTRE', "Autre situation (à préciser)"),
    ]
    beneficiaire = models.ForeignKey('beneficiaire.Beneficiaire', on_delete=models.CASCADE, related_name='saisines_copp')
    mds = models.ForeignKey('mds.MDS', on_delete=models.PROTECT, related_name='saisines_copp')
    commission = models.ForeignKey(CommissionPublicsPrioritaires, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='saisines')
    statut = models.CharField(max_length=12, choices=STATUTS, default=BROUILLON)
    donnees = models.JSONField(default=dict, blank=True)
    motifs = models.JSONField(default=list, blank=True)
    motif_autre = models.CharField("Autre motif", max_length=200, blank=True)
    rapport_social = models.TextField("Rapport social", blank=True,
                                      help_text="Situation, démarches engagées, motif de la demande. Pas d'appréciation "
                                                "sur la personne ; seuls les faits utiles à la commission.")
    pieces = models.ManyToManyField('ged.DocumentGED', blank=True, related_name='saisines_copp',
                                    help_text="Justificatifs joints (déposés dans la GED de l'usager)")
    decision = models.TextField("Décision ou préconisation de la commission", blank=True)
    date_decision = models.DateField(null=True, blank=True)
    historique = models.JSONField(default=list, blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name='saisines_copp')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Saisine de la commission des publics prioritaires"
        verbose_name_plural = "Saisines de la commission des publics prioritaires"
        ordering = ['-date_creation']

    def __str__(self):
        return f"COPP – {self.beneficiaire} ({self.get_statut_display()})"

    @property
    def modifiable(self):
        return self.statut == self.BROUILLON

    def libelles_motifs(self):
        m = dict(self.MOTIFS)
        out = [m[c] for c in self.motifs if c in m and c != 'AUTRE']
        if 'AUTRE' in self.motifs:
            out.append(self.motif_autre or "Autre")
        return out

    tracer = DemandeFSL.tracer
