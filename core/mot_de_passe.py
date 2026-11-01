# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# core/mot_de_passe.py
"""
Mot de passe oublié et réinitialisation (règle de la direction) :
  - l'agent signale l'oubli : l'administration reçoit un message CID (qui, date et heure) ;
  - l'administrateur réinitialise : mot de passe provisoire = initiales du prénom et du nom en majuscules
    + date du jour jjmmaaaa (ex. AS01112026), à changer dès la connexion suivante.
"""
import unicodedata

from django.utils import timezone


def _sans_accent(texte):
    return unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()


def mot_de_passe_provisoire(user, jour=None):
    jour = jour or timezone.localdate()
    initiales = (_sans_accent(user.first_name)[:1] + _sans_accent(user.last_name)[:1]).upper()
    if len(initiales) < 2:
        initiales = _sans_accent(user.username)[:2].upper()
    return f"{initiales}{jour:%d%m%Y}"


def reinitialiser(user):
    """Applique le mot de passe provisoire et oblige à le changer. Retourne le mot de passe provisoire."""
    mdp = mot_de_passe_provisoire(user)
    user.set_password(mdp)
    user.force_change_password = True
    user.save(update_fields=["password", "force_change_password"])
    return mdp


def administrateurs():
    """Ceux qui réinitialisent les mots de passe : super-administrateurs et gestionnaires des accès."""
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    User = get_user_model()
    return User.objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(profils__capacites__code="peut_gerer_acces")).distinct()


def peut_reinitialiser(admin, cible):
    if not admin.is_authenticated or admin.pk == cible.pk:
        return False
    if admin.is_superuser:
        return True
    return admin.a_la_capacite("peut_gerer_acces") and admin.peut_gerer_le_compte(cible)


def signaler_oubli(user):
    """Message CID à chaque administrateur (une fois toutes les 15 minutes au plus). Retourne le nombre envoyé."""
    from datetime import timedelta
    from django.urls import reverse
    from messagerie.models import Message, StatutLecture
    reference = f"MDP-{user.pk}"
    if Message.objects.filter(reference=reference, created_at__gte=timezone.now() - timedelta(minutes=15)).exists():
        return 0
    maintenant = timezone.localtime()
    nom = user.get_full_name() or user.username
    n = 0
    for admin in administrateurs().exclude(pk=user.pk):
        msg = Message.objects.create(
            expediteur=user, destinataire=admin, objet=f"Mot de passe oublié : {nom} ({user.username})",
            contenu=(f"{nom} (identifiant « {user.username} ») a signalé avoir oublié son mot de passe "
                     f"le {maintenant:%d/%m/%Y} à {maintenant:%H:%M}.\n\n"
                     f"Pour le réinitialiser : {reverse('core:reinitialiser_mot_de_passe', args=[user.pk])}\n"
                     f"Le mot de passe provisoire sera ses initiales en majuscules suivies de la date du jour "
                     f"(jjmmaaaa) ; il devra le changer dès sa connexion.\n\nMessage automatique de CID."),
            motif="demande_support", priorite="importante", reference=reference)
        StatutLecture.objects.create(message=msg, utilisateur=admin, type_reception="destinataire")
        n += 1
    return n
