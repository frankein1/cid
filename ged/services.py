# ged/services.py

from django.core.files.base import ContentFile
from ged.models import DocumentGED

def stocker_pdf_afase(*, demande, buffer, user):
    """
    Stockage FINAL du PDF AFASE dans la GED.
    Appelé UNE SEULE FOIS à la validation.
    """

    filename = f"AFASE_{demande.id}_DECISION.pdf"

    # Assure-toi que le curseur du buffer est au début
    buffer.seek(0)
    content = buffer.read()
    file = ContentFile(content, name=filename)

    # Création de l'entrée GED
    doc = DocumentGED.objects.create(
        content_object=demande,
        type_document="AFASE_DECISION",
        titre=f"Décision AFASE - Dossier {demande.id}",
        confidentialite="RESTREINT",
        uploaded_by=user,
    )

    # Affectation du fichier (déclenche le stockage physique)
    doc._uploaded_file = file
    doc.save()

    # Liaison directe sur la demande pour un accès rapide
    demande.document_final = doc
    demande.save(update_fields=["document_final"])

    # Remettre le curseur au début pour une éventuelle réutilisation (ex: FileResponse)
    buffer.seek(0)

    return doc
