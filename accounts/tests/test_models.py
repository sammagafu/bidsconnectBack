from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from ..models import CustomUser, Company, CompanyUser, CompanyInvitation, CompanyDocument, AuditLog
from ..constants import ROLE_CHOICES, MAX_COMPANY_USERS
import uuid

class CustomUserModelTests(TestCase):
    def test_create_user(self):
        user = CustomUser.objects.create_user(
            email="test@example.com",
            password="TestPass123",
            phone_number="1234567890"
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("TestPass123"))
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        superuser = CustomUser.objects.create_superuser(
            email="admin@example.com",
            password="AdminPass123"
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_user_str(self):
        user = CustomUser.objects.create_user(email="test@example.com", password="TestPass123")
        self.assertEqual(str(user), "test@example.com")

class CompanyModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )

    def test_company_creation(self):
        company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)
        self.assertEqual(company.slug, str(company.id))
        self.assertEqual(company.company_users.count(), 1)
        self.assertEqual(company.company_users.first().role, "owner")
        self.assertIsInstance(company.id, uuid.UUID)
        self.assertEqual(company.status, 'active')

    def test_company_max_per_user(self):
        for i in range(3):
            Company.objects.create(name=f"Company {i}", owner=self.user, created_by=self.user)
        with self.assertRaises(ValidationError):
            Company(name="Excess Company", owner=self.user, created_by=self.user).full_clean()

    def test_soft_delete(self):
        company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)
        company.soft_delete()
        self.assertIsNotNone(company.deleted_at)
        self.assertEqual(company.status, 'inactive')

class CompanyUserModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)

    def test_max_users_per_company(self):
        for i in range(MAX_COMPANY_USERS - 1):
            user = CustomUser.objects.create_user(email=f"user{i}@example.com", password="TestPass123")
            CompanyUser.objects.create(company=self.company, user=user, role="user")
        new_user = CustomUser.objects.create_user(email="excess@example.com", password="TestPass123")
        with self.assertRaises(ValidationError):
            CompanyUser(company=self.company, user=new_user, role="user").full_clean()

    def test_owner_role_protection(self):
        owner = self.company.company_users.get(role="owner")
        owner.role = "admin"
        with self.assertRaises(ValidationError):
            owner.full_clean()

class CompanyInvitationModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)

    def test_invitation_creation(self):
        invitation = CompanyInvitation.objects.create(
            company=self.company,
            invited_email="invited@example.com",
            invited_by=self.user,
            role="admin"
        )
        self.assertIsNotNone(invitation.token)
        self.assertFalse(invitation.accepted)
        self.assertTrue(invitation.expires_at > timezone.now())

class CompanyDocumentModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)

    def test_document_upload_owner_only(self):
        non_owner = CustomUser.objects.create_user(
            email="nonowner@example.com",
            password="TestPass123"
        )
        document = CompanyDocument(
            company=self.company,
            uploaded_by=non_owner,
            document_type="contract",
            document_file="dummy.pdf"
        )
        with self.assertRaises(ValidationError):
            document.full_clean()