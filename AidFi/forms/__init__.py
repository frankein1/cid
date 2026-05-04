# AidFi/forms/__init__.py
if beneficiaire: self.fields['documents_ged'].queryset = DocumentGED.objects.filter(content_type=ContentType.objects.get_for_model(beneficiaire), object_id=beneficiaire.id)
