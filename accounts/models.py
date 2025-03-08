import uuid
from django.db import models, transaction
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import Group, Permission
import secrets
from .constants import ROLE_CHOICES, DOCUMENT_TYPE_CHOICES, MAX_COMPANY_USERS
from django.conf import settings

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        related_name="customuser_groups",
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        related_name="customuser_permissions",
        related_query_name="customuser",
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

class Company(models.Model):
    """
    Represents a company in the system with comprehensive details for identification,
    operations, legal compliance, and auditing.
    """
    
    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the company (UUID)."
    )
    
    # Ownership
    owner = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name="companies",
        help_text="The user who owns this company."
    )
    
    # Basic Information
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="The official name of the company (must be unique)."
    )
    slug = models.SlugField(
        unique=True,
        blank=True,
        help_text="URL-friendly identifier for the company (optional, unique)."
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="A brief description of the company's purpose, services, or industry."
    )
    industry = models.CharField(
        max_length=100,
        blank=True,
        help_text="The industry the company operates in (e.g., tech, healthcare, finance)."
    )
    website = models.URLField(
        blank=True,
        null=True,
        help_text="The company's official website URL."
    )
    logo = models.ImageField(
        upload_to='company_logos/',
        blank=True,
        null=True,
        help_text="The company's logo for branding purposes."
    )
    
    # Contact Information
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="The company's primary contact email."
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="The company's primary phone number."
    )
    address = models.TextField(
        blank=True,
        null=True,
        help_text="The company's physical or mailing address."
    )
    
    # Legal and Compliance Information
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="The company's tax identification number or Employer Identification Number (EIN)."
    )
    registration_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="The company's registration number (e.g., for incorporation or business licenses)."
    )
    founded_date = models.DateField(
        blank=True,
        null=True,
        help_text="The date the company was founded."
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text="The country or region where the company is registered."
    )
    
    # Operational Information
    COMPANY_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]
    status = models.CharField(
        max_length=20,
        choices=COMPANY_STATUS_CHOICES,
        default='active',
        help_text="The operational status of the company (e.g., active, inactive, suspended)."
    )
    employee_count = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="The number of employees in the company."
    )
    parent_company = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subsidiaries',
        help_text="The parent company, if this company is a subsidiary (self-referential)."
    )
    
    # Soft Deletion
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the company was soft-deleted."
    )
    
    # Audit and Tracking Information
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the company record was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the company record was last updated."
    )
    created_by = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_companies',
        help_text="The user who created the company record."
    )
    
    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name', 'slug']),
            models.Index(fields=['owner']),
            models.Index(fields=['deleted_at']),
        ]
    
    def __str__(self):
        return self.name
    
    def clean(self):
        if self.owner.companies.filter(deleted_at__isnull=True).exclude(id=self.id).count() >= 3:
            raise ValidationError("Maximum of 3 companies per user allowed.")

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.full_clean()
            if not self.slug:
                self.slug = str(self.id)
            super().save(*args, **kwargs)
            
            if not self.company_users.filter(user=self.owner).exists():
                CompanyUser.objects.create(
                    company=self,
                    user=self.owner,
                    role='owner'
                )

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.status = 'inactive'
        self.save()

class CompanyUser(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_users')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'user')

    def clean(self):
        original = CompanyUser.objects.filter(pk=self.pk).first()
        
        if original and original.role == 'owner' and self.role != 'owner':
            raise ValidationError("Cannot change owner's role.")
            
        if self.role == 'owner':
            existing_owners = self.company.company_users.filter(role='owner')
            if self.pk:
                existing_owners = existing_owners.exclude(pk=self.pk)
            if existing_owners.exists():
                raise ValidationError("A company can only have one owner.")

        if self._state.adding and self.company.company_users.count() >= MAX_COMPANY_USERS:
            raise ValidationError(f"Maximum of {MAX_COMPANY_USERS} users per company.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class CompanyInvitation(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    invited_email = models.EmailField()
    invited_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=getattr(settings, 'INVITATION_EXPIRY_DAYS', 7))
        super().save(*args, **kwargs)

class CompanyDocument(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    document_file = models.FileField(upload_to='company_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.uploaded_by != self.company.owner:
            raise ValidationError("Only company owners can upload documents.")

class AuditLog(models.Model):
    action = models.CharField(max_length=50)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='accounts_audit_logs'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField()