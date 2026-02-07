# core/signals.py

from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import Group
from core.models.user import User  # adapte l'import si besoin


@receiver(m2m_changed, sender=User.profils.through)
def sync_user_groups_from_profils(sender, instance, action, reverse, pk_set, **kwargs):
    """
    À chaque changement sur user.profils, synchronise les groupes Django
    pour que l'utilisateur appartienne aux Group qui portent le même code
    que ses Profils.
    """
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    user = instance

    # Récupérer tous les codes de profil de l'utilisateur
    profil_codes = list(user.profils.values_list("code", flat=True))

    # Nom des groupes attendus = mêmes codes
    expected_group_names = set(profil_codes)

    # Groupes actuels de l'utilisateur
    current_groups = set(user.groups.values_list("name", flat=True))

    # Groupes à retirer = tout ce qui ne correspond plus à un profil
    groups_to_remove = current_groups - expected_group_names
    if groups_to_remove:
        user.groups.remove(*Group.objects.filter(name__in=groups_to_remove))

    # Groupes à ajouter
    groups_to_add = expected_group_names - current_groups
    for group_name in groups_to_add:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
