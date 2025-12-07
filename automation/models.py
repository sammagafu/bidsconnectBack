# automation/models.py
import uuid
from django.db import models

class PowerOfAttorney(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name = models.CharField(max_length=255)
    address = models.TextField()
    po_box = models.CharField(max_length=50)
    attorney_name = models.CharField(max_length=255)
    attorney_address = models.TextField()
    tender_no = models.CharField(max_length=100)
    tender_description = models.TextField()
    date = models.DateField()
    board_resolution_no = models.CharField(max_length=50)
    board_resolution_year = models.IntegerField()

class TenderSecuringDeclaration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    procuring_entity = models.CharField(max_length=255)
    tender_no = models.CharField(max_length=100)
    tender_description = models.TextField()
    date = models.DateField()
    signer_name = models.CharField(max_length=255)
    signer_capacity = models.CharField(max_length=255)

class LitigationHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name = models.CharField(max_length=255)
    address = models.TextField()
    po_box = models.CharField(max_length=50)
    tender_description = models.TextField()
    date = models.DateField()

class CoverLetter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    recipient_title = models.CharField(max_length=255)
    recipient_name = models.CharField(max_length=255, blank=True)
    recipient_address = models.TextField()
    reference_no = models.CharField(max_length=100)
    company_description = models.TextField()
    attached_docs_list = models.TextField()  # e.g., comma-separated
    compliance_certs = models.TextField()
    agency_dealership = models.TextField()
    lease_agreement = models.TextField()
    litigation_decl = models.TextField()
    similar_performance = models.TextField()
    financial_info = models.TextField()
    physical_address = models.TextField()
    contact_person = models.CharField(max_length=255)
    contact_position = models.CharField(max_length=255)
    contact_mobile = models.CharField(max_length=50)
    contact_email = models.EmailField()
    bank_name = models.CharField(max_length=255)
    branch_name = models.CharField(max_length=255)
    account_name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50)
    account_number = models.CharField(max_length=100)
    swift_code = models.CharField(max_length=50)