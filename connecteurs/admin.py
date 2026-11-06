# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# connecteurs/admin.py
from django.contrib import admin

from .models import SituationExterne, JournalAppelAPI


@admin.register(SituationExterne)
class SituationExterneAdmin(admin.ModelAdmin):
    list_display = ('beneficiaire', 'source', 'statut_appel', 'resume', 'date_maj', 'maj_par', 'environnement')
    list_filter = ('source', 'statut_appel', 'environnement')
    search_fields = ('beneficiaire__nom', 'beneficiaire__code_interne')


@admin.register(JournalAppelAPI)
class JournalAppelAPIAdmin(admin.ModelAdmin):
    list_display = ('date', 'utilisateur', 'beneficiaire', 'source', 'code_http', 'statut_appel', 'environnement')
    list_filter = ('source', 'statut_appel', 'environnement')
    readonly_fields = [f.name for f in JournalAppelAPI._meta.fields]


from .models import CompteRDVSP, LienUsagerRDVSP, AppelRDVSP  # noqa: E402


@admin.register(CompteRDVSP)
class CompteRDVSPAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'agent_id', 'expire_le', 'date_maj')
    exclude = ('jeton_acces', 'jeton_renouvellement')   # les jetons ne s'affichent jamais
    readonly_fields = ('utilisateur', 'agent_id', 'expire_le', 'date_maj')


@admin.register(LienUsagerRDVSP)
class LienUsagerRDVSPAdmin(admin.ModelAdmin):
    list_display = ('beneficiaire', 'usager_rdvsp_id', 'date_creation')
    search_fields = ('beneficiaire__nom', 'beneficiaire__code_interne', 'usager_rdvsp_id')


@admin.register(AppelRDVSP)
class AppelRDVSPAdmin(admin.ModelAdmin):
    list_display = ('date', 'utilisateur', 'beneficiaire', 'action', 'code_http', 'reussi')
    list_filter = ('action', 'reussi')
    readonly_fields = [f.name for f in AppelRDVSP._meta.fields]


from .models import (AbsenceRDVSP, AvisRDVSP, MdsRDVSP, MotifRDVSP, ParametresRDVSP, PlageRDVSP,  # noqa: E402
                     RdvRDVSP)


@admin.register(ParametresRDVSP)
class ParametresRDVSPAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'compte_synchro', 'semaines_publication', 'derniere_synchro')
    readonly_fields = ('derniere_synchro',)
    autocomplete_fields = ()

    def has_add_permission(self, request):
        return not ParametresRDVSP.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MdsRDVSP)
class MdsRDVSPAdmin(admin.ModelAdmin):
    list_display = ('mds', 'organisation_sp_id', 'en_ligne', 'lieu_sp_id', 'avis_declare')
    list_editable = ('en_ligne',)


@admin.register(MotifRDVSP)
class MotifRDVSPAdmin(admin.ModelAdmin):
    list_display = ('nom', 'duree_minutes', 'delai_min_heures', 'delai_max_jours', 'plafond_demi_journee',
                    'sur_invitation', 'actif')


class _Lecture(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PlageRDVSP)
class PlageRDVSPAdmin(_Lecture):
    list_display = ('agent', 'mds', 'jour_semaine', 'heure_debut', 'heure_fin', 'premier_jour', 'dernier_jour',
                    'plage_sp_id', 'neutralisee')
    list_filter = ('neutralisee', 'mds')


@admin.register(AbsenceRDVSP)
class AbsenceRDVSPAdmin(_Lecture):
    list_display = ('date', 'heure_debut', 'heure_fin', 'agent', 'raison', 'absence_sp_id')
    list_filter = ('raison',)


@admin.register(RdvRDVSP)
class RdvRDVSPAdmin(_Lecture):
    list_display = ('debut', 'motif', 'agent', 'beneficiaire', 'cree_par_usager', 'statut_sp', 'annule_le',
                    'a_rapprocher')
    list_filter = ('cree_par_usager', 'statut_sp', 'a_rapprocher')


@admin.register(AvisRDVSP)
class AvisRDVSPAdmin(_Lecture):
    list_display = ('recu_le', 'modele', 'evenement', 'objet_sp_id', 'traite', 'erreur')
    list_filter = ('traite', 'modele')


from .models import CampagneInvitations, InvitationRSA, ReservationEnLigne  # noqa: E402


@admin.register(CampagneInvitations)
class CampagneInvitationsAdmin(admin.ModelAdmin):
    list_display = ('mois', 'preparee_le', 'envoi_prevu', 'envoyee_le')


@admin.register(InvitationRSA)
class InvitationRSAAdmin(_Lecture):
    list_display = ('campagne', 'beneficiaire', 'referent', 'cochee', 'envoyee_le', 'mode', 'erreur')
    list_filter = ('campagne', 'cochee', 'mode')
    exclude = ('lien',)   # lien personnel de réservation : pas affiché


@admin.register(ReservationEnLigne)
class ReservationEnLigneAdmin(_Lecture):
    list_display = ('beneficiaire', 'suspendue', 'modifiee_par', 'modifiee_le')
    list_filter = ('suspendue',)


from .models import LieuExterneRDVSP  # noqa: E402


@admin.register(LieuExterneRDVSP)
class LieuExterneRDVSPAdmin(admin.ModelAdmin):
    list_display = ('nom', 'mds_sp', 'adresse', 'lieu_sp_id')
    list_filter = ('mds_sp',)


from .models import ImportInclusion, ServiceInclusion  # noqa: E402


@admin.register(ServiceInclusion)
class ServiceInclusionAdmin(admin.ModelAdmin):
    list_display = ('nom', 'structure_nom', 'commune', 'type', 'frais', 'source', 'date_maj')
    list_filter = ('source', 'type', 'frais')
    search_fields = ('nom', 'structure_nom', 'commune')

    def has_add_permission(self, request):
        return False      # importé depuis data·inclusion


@admin.register(ImportInclusion)
class ImportInclusionAdmin(admin.ModelAdmin):
    list_display = ('debut', 'fin', 'departements', 'structures', 'services', 'retires', 'erreur')


from .models import EcartSituation, PrestationRelevee  # noqa: E402


@admin.register(EcartSituation)
class EcartSituationAdmin(admin.ModelAdmin):
    list_display = ('beneficiaire', 'nature', 'signale_le', 'regle_le')
    list_filter = ('nature',)
    raw_id_fields = ('beneficiaire',)


@admin.register(PrestationRelevee)
class PrestationReleveeAdmin(admin.ModelAdmin):
    list_display = ('beneficiaire', 'prestation', 'montant', 'date_releve', 'saisi_par')
    raw_id_fields = ('beneficiaire',)
