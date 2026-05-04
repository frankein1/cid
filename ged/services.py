# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

from django.core.files.base import ContentFile
from ged.models import DocumentGED, DocumentType


def stocker_pdf_afase(*, demande, buffer, user):
    """
    Stockage FINAL du PDF AFASE dans la GED.
    Appelé UNE SEULE FOIS à la validation de la décision.
    
    Paramètres :
    - demande : la demande AFASE concernée
    - buffer  : le PDF généré en mémoire
    - user    : l'utilisateur qui valide et archive le document
    """

    # Nom du fichier physique qui sera stocké
    filename = f"AFASE_{demande.id}_DECISION.pdf"

    # On s'assure que la lecture du buffer commence au début
    buffer.seek(0)
    content = buffer.read()
    file = ContentFile(content, name=filename)

    # ------------------------------------------------------------------
    # Récupération du type GED correspondant
    # IMPORTANT :
    # - DocumentGED.type_document est un ForeignKey vers DocumentType
    # - on ne peut donc PAS mettre une chaîne ("AFASE_DECISION")
    # - il faut un vrai objet DocumentType
    # ------------------------------------------------------------------
    type_document, _ = DocumentType.objects.get_or_create(
        code="AFASE_DECISION",
        defaults={
            "nom": "Décision AFASE",
            "categorie": "finances",
            "extensions_autorisees": ["pdf"],
            "taille_max_mb": 10,
            "est_sensible": True,
            "actif": True,
        },
    )

    # ------------------------------------------------------------------
    # Création de l'entrée GED
    # uploaded_by = user est conservé :
    # cela permet de tracer qui a validé / archivé le document.
    # ------------------------------------------------------------------
    doc = DocumentGED.objects.create(
        content_object=demande,
        type_document=type_document,
        titre=f"Décision AFASE - Dossier {demande.id}",
        confidentialite="RESTREINT",
        uploaded_by=user,
    )

    # Affectation du fichier :
    # doc.save() déclenche ensuite le stockage physique via le modèle GED
    doc._uploaded_file = file
    doc.save()

    # ------------------------------------------------------------------
    # Liaison directe sur la demande :
    # utile pour accéder rapidement au document final depuis AFASE
    # ------------------------------------------------------------------
    demande.document_final = doc
    demande.save(update_fields=["document_final"])

    # On replace le curseur au début pour un éventuel réemploi du buffer
    buffer.seek(0)

    return doc
