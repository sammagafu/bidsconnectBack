import uuid
import secrets
from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
)
from django.db.models import Avg

from .constants import (
    ROLE_CHOICES,
    DOCUMENT_TYPE_CHOICES,
    DOCUMENT_CATEGORY_CHOICES,
    MAX_COMPANY_USERS,
    MAX_COMPANIES_PER_USER,
    DEFAULT_DOCUMENT_EXPIRY_DAYS,
    DOCUMENT_EXPIRY_NOTIFICATION_DAYS,
    INVITATION_EXPIRY_DAYS,
)


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not extra_fields['is_staff'] or not extra_fields['is_superuser']:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True")
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        Group, blank=True,
        related_name="customuser_groups",
        related_query_name="customuser"
    )
    user_permissions = models.ManyToManyField(
        Permission, blank=True,
        related_name="customuser_permissions",
        related_query_name="customuser"
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="companies")
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    registration_number = models.CharField(max_length=50, blank=True, null=True)
    founded_date = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True)

    COMPANY_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]
    status = models.CharField(max_length=20, choices=COMPANY_STATUS_CHOICES, default='active')
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(blank=True, null=True)
    employee_count = models.PositiveIntegerField(blank=True, null=True)
    parent_company = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subsidiaries'
    )

    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_companies'
    )

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name', 'slug']),
            models.Index(fields=['owner']),
            models.Index(fields=['deleted_at']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """
        Ensure a user can only own one company.
        """
        existing = self.owner.companies.filter(deleted_at__isnull=True).exclude(id=self.id).count()
        if existing >= MAX_COMPANIES_PER_USER:
            raise ValidationError(f"A user can only own {MAX_COMPANIES_PER_USER} company.")

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.full_clean()
            if not self.slug:
                self.slug = str(self.id)
            super().save(*args, **kwargs)
            # Ensure owner is in CompanyUser
            if not self.company_users.filter(user=self.owner).exists():
                CompanyUser.objects.create(company=self, user=self.owner, role='owner')

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.status = 'inactive'
        self.save()

    def verify(self, user):
        if not isinstance(user, CustomUser):
            raise ValidationError("Invalid user type.")
        self.is_verified = True
        self.verification_date = timezone.now()
        self.save(update_fields=['is_verified', 'verification_date'])
        AuditLog.objects.create(
            action="company_verified",
            user=user,
            details={"company_id": str(self.id), "company_name": self.name}
        )

    @property
    def average_rating(self):
        return self.reviews.aggregate(Avg('rating'))['rating__avg'] or 0


class CompanyUser(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='company_users'
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'user')

    def clean(self):
        """
        Enforce:
        - One owner per company
        - Max 5 members per company
        """
        original = CompanyUser.objects.filter(pk=self.pk).first()
        # Prevent demoting owner
        if original and original.role == 'owner' and self.role != 'owner':
            raise ValidationError("Cannot change owner's role.")

        # Only one owner
        if self.role == 'owner':
            owners = self.company.company_users.filter(role='owner')
            if self.pk:
                owners = owners.exclude(pk=self.pk)
            if owners.exists():
                raise ValidationError("A company can only have one owner.")

        # Max users per company (including owner)
        if self._state.adding:
            count = self.company.company_users.count()
            if count >= MAX_COMPANY_USERS:
                raise ValidationError(f"A company can only have up to {MAX_COMPANY_USERS} members.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CompanyInvitation(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='invitations'
    )
    invited_email = models.EmailField()
    invited_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='sent_invitations'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    accepted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['token'])]

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=INVITATION_EXPIRY_DAYS)
        super().save(*args, **kwargs)


class CompanyDocument(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='documents'
    )
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    document_category = models.CharField(
        max_length=50, choices=DOCUMENT_CATEGORY_CHOICES, default='other'
    )
    document_file = models.FileField(upload_to='company_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_expired = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=[
            ('Approved', 'Approved'),
            ('Denied', 'Denied'),
            ('Under Review', 'Under Review')
        ], default='Under Review'
    )
    notification_sent = models.JSONField(default=dict, blank=True)
    notification_attempts = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_expired']),
            models.Index(fields=['document_category']),
            models.Index(fields=['uploaded_at']),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.document_file.name}"

    def clean(self):
        if self.uploaded_by != self.company.owner:
            raise ValidationError("Only company owners can upload documents.")
        if self.expires_at and self.expires_at < timezone.now():
            raise ValidationError("Expiration date cannot be in the past.")

    def reset_notifications(self):
        threshold = timezone.now() + timedelta(days=DOCUMENT_EXPIRY_NOTIFICATION_DAYS)
        if self.expires_at and self.expires_at > threshold:
            self.notification_sent = {}
            self.notification_attempts = {}

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=DEFAULT_DOCUMENT_EXPIRY_DAYS)
        self.is_expired = self.expires_at < timezone.now()
        self.reset_notifications()
        self.full_clean()
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    action = models.CharField(max_length=50)
    user = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True,
        related_name='accounts_audit_logs'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField()

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.action} - {self.timestamp}"
