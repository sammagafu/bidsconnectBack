# accounts/tests/test_api.py

import io
import uuid

from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import (
    Company, CompanyUser, CompanyInvitation,
    CompanyDocument, AuditLog
)
from accounts.constants import (
    MAX_COMPANIES_PER_USER,
    MAX_COMPANY_USERS,
    DEFAULT_DOCUMENT_EXPIRY_DAYS,
    INVITATION_EXPIRY_DAYS,
    DOCUMENT_EXPIRY_NOTIFICATION_DAYS
)

User = get_user_model()


class APITestSuite(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create two users
        self.owner = User.objects.create_user(
            email='owner@example.com', password='pass1234'
        )
        self.other = User.objects.create_user(
            email='other@example.com', password='pass1234'
        )
        # Force-login as owner by default
        self.client.force_authenticate(self.owner)

    def test_registration_endpoint(self):
        """POST /auth/register/"""
        self.client.logout()
        url = reverse('user-register')
        resp = self.client.post(url, {
            'email': 'new@example.com',
            'password': 'newpass123',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '0712345678'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

    def test_company_crud(self):
        """List, Create, Retrieve, Update, Delete Company"""
        list_url = reverse('company-list')
        # Initially empty
        resp = self.client.get(list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json(), [])

        # Create
        resp = self.client.post(list_url, {
            'name': 'Acme Ltd',
            'description': 'Test company',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.json()
        company_id = data['id']
        self.assertEqual(data['name'], 'Acme Ltd')
        self.assertEqual(data['owner_email'], self.owner.email)

        # Retrieve
        detail_url = reverse('company-detail', args=[company_id])
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['id'], company_id)

        # Update
        resp = self.client.patch(detail_url, {'description': 'Updated'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['description'], 'Updated')

        # Soft Delete
        resp = self.client.delete(detail_url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        co = Company.objects.get(id=company_id)
        self.assertIsNotNone(co.deleted_at)

    def test_company_user_management(self):
        """Add, list, update, delete CompanyUser"""
        # Prep a company
        co = Company.objects.create(owner=self.owner, name='C1')
        # Add other as member
        url = reverse('company-users', args=[co.id])
        resp = self.client.post(url, {'user': self.other.id, 'role': 'user'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        cu_id = resp.json()['id']

        # List
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.json()), 2)  # owner + other

        # Update role
        detail = reverse('company-user-detail', args=[co.id, cu_id])
        resp = self.client.patch(detail, {'role': 'manager'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['role'], 'manager')

        # Cannot modify owner
        owner_cu = CompanyUser.objects.get(company=co, user=self.owner)
        with self.assertRaises(ValidationError):
            owner_cu.role = 'user'
            owner_cu.full_clean()

        # Delete
        resp = self.client.delete(detail)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CompanyUser.objects.filter(id=cu_id).exists())

    def test_invitations(self):
        """Invite user, list, retrieve, delete, accept"""
        co = Company.objects.create(owner=self.owner, name='C2')
        list_url = reverse('invitation-list', args=[co.id])

        # Create
        resp = self.client.post(list_url, {
            'invited_email': 'invitee@example.com',
            'role': 'user'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.json()['id']
        token = CompanyInvitation.objects.get(id=inv_id).token

        # List
        resp = self.client.get(list_url)
        self.assertEqual(len(resp.json()), 1)

        # Retrieve
        detail_url = reverse('invitation-detail', args=[co.id, inv_id])
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Delete
        resp = self.client.delete(detail_url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        # Re-create and accept
        inv = CompanyInvitation.objects.create(
            company=co, invited_email=self.other.email,
            invited_by=self.owner, role='user'
        )
        accept_url = reverse('accept-invitation', args=[co.id, inv.token])
        # simulate other user
        self.client.force_authenticate(self.other)
        resp = self.client.post(accept_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(CompanyUser.objects.filter(company=co, user=self.other).exists())

    def test_document_endpoints(self):
        """Create, list, retrieve, delete documents"""
        co = Company.objects.create(owner=self.owner, name='C3')
        url = reverse('document-list', args=[co.id])
        pdf = SimpleUploadedFile('f.pdf', b'%PDF-1.4\n%', content_type='application/pdf')

        # Upload
        resp = self.client.post(url, {
            'document_type': 'contract',
            'document_category': 'legal',
            'document_file': pdf
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        doc_id = resp.json()['id']

        # List
        resp = self.client.get(url)
        self.assertEqual(len(resp.json()), 1)

        # Retrieve
        detail = reverse('document-detail', args=[co.id, doc_id])
        resp = self.client.get(detail)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Delete
        resp = self.client.delete(detail)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CompanyDocument.objects.filter(id=doc_id).exists())

    def test_profile_and_special_lists(self):
        """Profile view, owner-list, admin-list"""
        # Profile GET
        url = reverse('user-profile')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['email'], self.owner.email)

        # Profile PATCH
        resp = self.client.patch(url, {
            'first_name': 'Own',
            'last_name': 'Er',
            'phone_number': '0787654321'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.first_name, 'Own')

        # Owner company list
        co1 = Company.objects.create(owner=self.owner, name='OwnerCo')
        url = reverse('owner-company-list')
        resp = self.client.get(url)
        self.assertEqual(len(resp.json()), 1)

        # Admin list (only for is_staff)
        self.owner.is_staff = True
        self.owner.save()
        url = reverse('admin-company-list')
        resp = self.client.get(url)
        self.assertTrue(resp.status_code, status.HTTP_200_OK)

    def test_url_reverse(self):
        """Ensure URL names resolve"""
        names = [
            ('company-list', []),
            ('company-detail', [uuid.uuid4()]),
            ('company-users', [uuid.uuid4()]),
            ('company-user-detail', [uuid.uuid4(), 1]),
            ('invitation-list', [uuid.uuid4()]),
            ('invitation-detail', [uuid.uuid4(), 1]),
            ('accept-invitation', [uuid.uuid4(), 'tkn']),
            ('document-list', [uuid.uuid4()]),
            ('document-detail', [uuid.uuid4(), 1]),
            ('user-profile', []),
            ('owner-company-list', []),
            ('admin-company-list', []),
        ]
        for name, args in names:
            url = reverse(name, args=args)
            self.assertTrue(url.startswith('/'))
