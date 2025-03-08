from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import CustomUser, Company, CompanyUser, CompanyInvitation, CompanyDocument
from ..constants import ROLE_CHOICES

class UserRegistrationViewTests(APITestCase):
    def test_register_user(self):
        url = '/api/v1/accounts/users/'  # Adjusted to match Djoser under api/v1/accounts/
        data = {
            "email": "test@example.com",
            "phone_number": "1234567890",
            "password": "TestPass123!"
        }
        response = self.client.post(url, data, format='json')
        if response.status_code != status.HTTP_201_CREATED:
            print("Response status:", response.status_code)
            print("Response content:", response.content.decode() if hasattr(response, 'content') else "No content")
            print("Request URL:", response.request['PATH_INFO'])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"Failed with status: {response.status_code}")
        self.assertEqual(CustomUser.objects.count(), 1)

class CompanyListViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_company(self):
        url = reverse('company-list')  # No namespace needed if not using it
        data = {"name": "Test Co", "description": "Test description"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Company.objects.first().owner, self.user)

    def test_list_companies(self):
        company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)
        url = reverse('company-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

class CompanyDetailViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_soft_delete_company(self):
        url = reverse('company-detail', kwargs={'id': str(self.company.id)})
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.company.refresh_from_db()
        self.assertIsNotNone(self.company.deleted_at)

class DocumentManagementViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_upload_document(self):
        url = reverse('document-list', kwargs={'company_id': str(self.company.id)})
        file = SimpleUploadedFile("test.pdf", b"dummy content", content_type="application/pdf")
        data = {"document_type": "contract", "document_file": file}
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CompanyDocument.objects.count(), 1)

class CompanyUserManagementViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)
        self.member = CustomUser.objects.create_user(
            email="member@example.com",
            password="TestPass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_add_company_user(self):
        url = reverse('company-users', kwargs={'company_id': str(self.company.id)})
        data = {"user": str(self.member.id), "role": "user"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CompanyUser.objects.count(), 2)

class InvitationListViewTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_invitation(self):
        url = reverse('invitation-list', kwargs={'company_id': str(self.company.id)})
        data = {"invited_email": "invited@example.com", "role": "admin"}
        response = self.client.post(url, data, format='json')
        if response.status_code != status.HTTP_201_CREATED:
            print("Response data:", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(CompanyInvitation.objects.count(), 1)