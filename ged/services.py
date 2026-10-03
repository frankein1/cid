# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================

from django.core.files.base import ContentFile
from ged.models import DocumentGED, DocumentType


def stocker_pdf_afase(demande, buffer, user):
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
    # Création de l'entrée GED, rattachée au BÉNÉFICIAIRE :
    # - visible sur sa fiche et dans la GED (barrière MDS appliquée)
    # - fichier physiquement stocké via add_new_version (version 1)
    # ------------------------------------------------------------------
    doc = DocumentGED.objects.create(
        content_object=demande.beneficiaire,
        type_document=type_document,
        titre=f"Décision AFASE - Dossier {demande.id}",
        confidentialite="RESTREINT",
        uploaded_by=user,
    )
    doc.add_new_version(
        buffer=ContentFile(content, name=filename),
        filename=filename,
        user=user,
        raison=f"Décision AFASE dossier {demande.id}",
    )

    # Liaison à la demande : le PDF apparaît dans ses documents
    from AidFi.models.m_generique import PieceJustificative
    PieceJustificative.objects.create(
        demande=demande, document_ged=doc,
        type_piece="DECISION", statut="VALIDE",
    )

    buffer.seek(0)
    return doc
