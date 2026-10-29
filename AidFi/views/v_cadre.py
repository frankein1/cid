# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

# AidFi/views/v_cadre.py
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render

from AidFi.models.m_afase import DemandeAFASE
from AidFi.models.m_cap import DemandeCAP


@login_required
def dashboard_cadre(request):
    """
    Tableau de bord cadre : AFASE à décider, CAP à décider et à remettre,
    limités aux MDS de l'utilisateur (l'administrateur voit tout).
    """
    user = request.user
    decide_afase = user.a_la_capacite("peut_decider")
    decide_cap = user.a_la_capacite("peut_valider_cheque_aidfi")
    if not (decide_afase or decide_cap):
        return HttpResponseForbidden("Accès refusé")

    def mes_mds(qs):
        if user.a_la_capacite("peut_administrer"):
            return qs
        from mds.models import UserMDSProfile
        ids = UserMDSProfile.objects.filter(user=user, actif=True).values_list("mds_id", flat=True)
        return qs.filter(beneficiaire__mds_id__in=ids)

    demandes = DemandeAFASE.objects.none()
    if decide_afase:
        # Les familles avec une mesure ASE relèvent de l'inspecteur enfance-famille
        demandes = mes_mds(DemandeAFASE.objects.filter(statut="DEPOSEE")) \
            .exclude(mesure_ase__in=("ENFANT_CONFIE", "ASSISTANCE_EDUCATIVE")) \
            .select_related("beneficiaire").order_by("date_creation")
    ajournees = mes_mds(DemandeAFASE.objects.filter(statut="AJO")) \
        .exclude(mesure_ase__in=("ENFANT_CONFIE", "ASSISTANCE_EDUCATIVE")) \
        .select_related("beneficiaire").order_by("date_ajournement") if decide_afase else []
    from AidFi.services import afase_delais
    demandes = list(demandes)
    for d in demandes + list(ajournees):
        try:
            afase_delais.envoyer_rappels(d)   # rappels de délais dus (une seule fois chacun)
        except Exception:
            pass
        d.delais = afase_delais.etat(d)

    caps = DemandeCAP.objects.none()
    if decide_cap:
        caps = mes_mds(DemandeCAP.objects.filter(statut__in=("DEPOSEE", "ACCORDEE"))) \
            .select_related("beneficiaire", "cree_par").order_by("date_creation")

    return render(
        request,
        "AidFi/dashboard_cadre.html",
        {
            "demandes": demandes,
            "ajournees": ajournees,
            "caps_a_decider": [c for c in caps if c.statut == "DEPOSEE"],
            "caps_a_remettre": [c for c in caps if c.statut == "ACCORDEE"],
            "decide_afase": decide_afase,
            "decide_cap": decide_cap,
        },
    )
