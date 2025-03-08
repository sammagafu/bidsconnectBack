from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import CustomUser, Company, CompanyUser, CompanyInvitation, CompanyDocument, AuditLog
import uuid

class AuditLogTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_audit_log_company_creation(self):
        url = reverse('company-list')
        data = {"name": "New Co", "description": "New company"}
        self.client.post(url, data, format='json')
        log = AuditLog.objects.get(action='company_creation')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.details['name'], "New Co")
        self.assertTrue(isinstance(uuid.UUID(log.details['company_id']), uuid.UUID))

    def test_audit_log_document_upload(self):
        url = reverse('document-list', kwargs={'company_id': str(self.company.id)})
        file = SimpleUploadedFile("test.pdf", b"dummy content", content_type="application/pdf")
        data = {"document_type": "contract", "document_file": file}
        self.client.post(url, data, format='multipart')
        log = AuditLog.objects.get(action='document_uploaded')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.details['company_id'], str(self.company.id))