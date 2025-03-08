from django.test import TestCase, RequestFactory
from rest_framework.exceptions import ValidationError
from ..serializers import (
    CustomUserCreateSerializer,
    CompanySerializer,
    CompanyUserSerializer,
    CompanyInvitationSerializer,
    CompanyDocumentSerializer
)
from ..models import CustomUser, Company, CompanyUser, CompanyInvitation
from django.core.files.uploadedfile import SimpleUploadedFile

class CustomUserCreateSerializerTests(TestCase):
    def test_valid_user_creation(self):
        data = {
            "email": "test@example.com",
            "phone_number": "1234567890",
            "password": "TestPass123!"  # Reverted to original
        }
        serializer = CustomUserCreateSerializer(data=data)
        is_valid = serializer.is_valid(raise_exception=False)
        if not is_valid:
            print("Validation errors:", serializer.errors)  # Debug output
        self.assertTrue(is_valid, f"Serializer validation failed: {serializer.errors}")
        user = serializer.save()
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.phone_number, "1234567890")

    def test_weak_password(self):
        data = {
            "email": "test@example.com",
            "phone_number": "1234567890",
            "password": "weak"
        }
        serializer = CustomUserCreateSerializer(data=data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

class CompanySerializerTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.factory = RequestFactory()

    def test_duplicate_company_name(self):
        Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)
        data = {"name": "Test Co"}
        request = self.factory.post('/fake-url', data)
        request.user = self.user
        serializer = CompanySerializer(data=data, context={'request': request})
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_uuid_slug(self):
        company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)
        serializer = CompanySerializer(company)
        self.assertEqual(serializer.data['slug'], str(company.id))

class CompanyDocumentSerializerTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="owner@example.com",
            password="TestPass123"
        )
        self.company = Company.objects.create(name="Test Co", owner=self.user, created_by=self.user)
        self.factory = RequestFactory()

    def test_file_size_validation(self):
        large_file = SimpleUploadedFile("large.pdf", b"0" * (11 * 1024 * 1024))
        data = {
            "document_type": "contract",
            "document_file": large_file,
        }
        request = self.factory.post('/fake-url', data)
        request.user = self.user
        serializer = CompanyDocumentSerializer(
            data=data,
            context={'request': request, 'view': {'kwargs': {'company_id': str(self.company.id)}}}
        )
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_file_type_validation(self):
        invalid_file = SimpleUploadedFile("image.png", b"dummy content")
        data = {
            "document_type": "contract",
            "document_file": invalid_file,
        }
        request = self.factory.post('/fake-url', data)
        request.user = self.user
        serializer = CompanyDocumentSerializer(
            data=data,
            context={'request': request, 'view': {'kwargs': {'company_id': str(self.company.id)}}}
        )
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)