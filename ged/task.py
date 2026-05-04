# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# ged/tasks.py

def check_expiration_documents():
    """Marque les documents qui arrivent à expiration sous 30 jours."""
    limite = timezone.now().date() + timedelta(days=30)
    
    # On ne cible que les documents actifs de dossiers actifs
    docs_a_notifier = DocumentGED.objects.filter(
        statut='VALIDE',
        alerte_active=True,
        date_expiration__lte=limite,
        notification_envoyee=False
    )
    
    for doc in docs_a_notifier:
        # On vérifie si le bénéficiaire est toujours "Actif" avant de notifier
        if hasattr(doc.content_object, 'est_actif') and doc.content_object.est_actif:
            doc.notification_envoyee = True
            doc.save()
            doc.log_action('ALERTE_EXPIRATION', None, "Document arrivant à expiration.")

    return docs_a_notifier.count()
