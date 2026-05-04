# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================
# AidFi/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail

from AidFi.models.m_generique import DemandeAide, SuiviDemande


@receiver(post_save, sender=DemandeAide)
def suivi_creation_demande(sender, instance, created, **kwargs):
    """
    Création initiale du suivi métier.
    Déclenché UNE SEULE FOIS.
    """
    if not created:
        return

    SuiviDemande.objects.create(
        demande=instance,
        statut_precedent="NEANT",
        statut_nouveau=instance.statut,
        agent=instance.cree_par,
    )


@receiver(post_save, sender=DemandeAide)
def alerte_depot_demande(sender, instance, created, **kwargs):
    """
    Alerte mail UNIQUEMENT lors du passage à DEPOSEE.
    """
    if created:
        return

    if instance.statut != "DEPOSEE":
        return

    send_mail(
        subject=f"Nouvelle demande AidFi déposée",
        message=f"Dossier {instance.id} prêt pour instruction.",
        from_email="noreply@ditas.fr",
        recipient_list=["cadre.mds@departement.fr"],
        fail_silently=True,
    )
