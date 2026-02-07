# planning/signals.py
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import CreneauRdv, JourBloque, HistoriqueCreneau
import json

User = get_user_model()


@receiver(pre_save, sender=CreneauRdv)
def creneau_pre_save(sender, instance, **kwargs):
    """Capture les changements avant sauvegarde pour l'historique"""
    if instance.pk:
        try:
            ancien = CreneauRdv.objects.get(pk=instance.pk)
            instance._anciennes_valeurs = {
                'statut': ancien.statut,
                'agent_id': ancien.agent_id,
                'beneficiaire_id': ancien.beneficiaire_id,
                'description': ancien.description,
                'type_rdv': ancien.type_rdv,
            }
        except CreneauRdv.DoesNotExist:
            instance._anciennes_valeurs = {}


@receiver(post_save, sender=CreneauRdv)
def creneau_post_save(sender, instance, created, **kwargs):
    """Crée une entrée d'historique après sauvegarde"""
    if created:
        action = 'CREATION'
        anciennes_valeurs = {}
        nouvelles_valeurs = {
            'statut': instance.statut,
            'agent_id': instance.agent_id,
            'beneficiaire_id': instance.beneficiaire_id,
            'description': instance.description,
            'type_rdv': instance.type_rdv,
        }
    else:
        action = 'MODIFICATION'
        anciennes_valeurs = getattr(instance, '_anciennes_valeurs', {})
        nouvelles_valeurs = {
            'statut': instance.statut,
            'agent_id': instance.agent_id,
            'beneficiaire_id': instance.beneficiaire_id,
            'description': instance.description,
            'type_rdv': instance.type_rdv,
        }
    
    # Créer l'entrée d'historique
    historique = HistoriqueCreneau.objects.create(
        creneau=instance,
        action=action,
        anciennes_valeurs=anciennes_valeurs,
        nouvelles_valeurs=nouvelles_valeurs
    )


@receiver(post_save, sender=JourBloque)
def jour_bloque_post_save(sender, instance, created, **kwargs):
    """Met à jour les créneaux affectés par un jour bloqué"""
    if created:
        # Annuler les créneaux affectés par ce blocage
        creneaux_affectes = CreneauRdv.objects.filter(
            date=instance.date,
            heure_debut__lt=instance.heure_fin,
            heure_fin__gt=instance.heure_debut
        )
        
        if instance.salle:
            creneaux_affectes = creneaux_affectes.filter(salle=instance.salle)
        
        if instance.agent:
            creneaux_affectes = creneaux_affectes.filter(agent=instance.agent)
        
        for creneau in creneaux_affectes:
            creneau.statut = 'ANNULE_MDS'
            creneau.description = f"Annulé automatiquement - {instance.get_raison_display()}: {instance.raison_detail}"
            creneau.save()


@receiver(post_delete, sender=JourBloque)
def jour_bloque_post_delete(sender, instance, **kwargs):
    """Restaure les créneaux affectés par un jour bloqué supprimé"""
    # Libérer les créneaux qui étaient annulés à cause de ce blocage
    creneaux_affectes = CreneauRdv.objects.filter(
        date=instance.date,
        statut='ANNULE_MDS',
        description__contains=instance.get_raison_display()
    )
    
    for creneau in creneaux_affectes:
        creneau.statut = 'DISPONIBLE'
        creneau.description = ""
        creneau.save()
