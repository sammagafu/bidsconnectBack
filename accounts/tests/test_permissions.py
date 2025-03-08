from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from ..models import CustomUser, Company, CompanyUser
from ..permissions import IsCompanyOwner, IsCompanyAdminOrOwner, IsCompanyMember

class PermissionTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.admin = CustomUser.objects.create_user(
            email="admin@example.com",
            password="TestPass123"
        )
        self.member = CustomUser.objects.create_user(
            email="member@example.com",
            password="TestPass123"
        )
        self.company = Company.objects.create(name="Test Co", owner=self.owner, created_by=self.owner)
        CompanyUser.objects.create(company=self.company, user=self.admin, role="admin")
        CompanyUser.objects.create(company=self.company, user=self.member, role="user")
        self.client = APIClient()

    def test_is_company_owner_permission(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse('company-detail', kwargs={'id': str(self.company.id)})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_is_company_admin_or_owner_permission(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('company-users', kwargs={'company_id': str(self.company.id)})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.member)
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_is_company_member_permission(self):
        self.client.force_authenticate(user=self.member)
        url = reverse('company-users', kwargs={'company_id': str(self.company.id)})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)