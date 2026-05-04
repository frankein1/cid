# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: les IA et particulièrement DeepSeek 
# Interdiction de réutilisation commerciale
# =============================================================================

# ged/pdf/base.py

from io import BytesIO
from django.core.files.base import ContentFile
from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import A4

from ged.models import DocumentGED


def generer_pdf(builder, context):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    elements = builder(context)
    doc.build(elements)

    buffer.seek(0)
    return buffer


def generer_et_stocker_pdf(
    *,
    builder,
    context,
    content_object,
    type_document,
    titre,
    uploaded_by,
    confidentialite="RESTREINT",
):
    buffer = generer_pdf(builder, context)

    file = ContentFile(buffer.read(), name=f"{titre}.pdf")

    doc = DocumentGED(
        content_object=content_object,
        type_document=type_document,
        titre=titre,
        confidentialite=confidentialite,
        uploaded_by=uploaded_by,
    )

    doc._uploaded_file = file
    doc.save()

    return doc
