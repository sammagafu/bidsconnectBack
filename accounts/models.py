import uuid
import secrets
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
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
        related_name="accounts_customuser_groups",
        related_query_name="customuser"
    )
    user_permissions = models.ManyToManyField(
        Permission, blank=True,
        related_name="accounts_customuser_permissions",
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
    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="accounts_companies"
    )
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    registration_number = models.CharField(max_length=50, blank=True, null=True)
    founded_date = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True)
    key_activities = models.TextField(blank=True)
    naics_code = models.CharField(max_length=10, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended')],
        default='active'
    )
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(blank=True, null=True)
    employee_count = models.PositiveIntegerField(blank=True, null=True)
    parent_company = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='accounts_subsidiaries'
    )

    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser, null=True, on_delete=models.SET_NULL, related_name='accounts_created_companies'
    )

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['owner', 'deleted_at']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while Company.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    @property
    def avg_annual_turnover(self):
        return self.annual_turnovers.aggregate(Avg('amount'))['amount__avg'] or 0

    def get_company_users(self):
        return self.company_users.filter(deleted_at__isnull=True)

class CompanyUser(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='accounts_company_users')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='accounts_company_users')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('company', 'user')
        indexes = [models.Index(fields=['company', 'user']), models.Index(fields=['role'])]

    def __str__(self):
        return f"{self.user.email} - {self.company.name} ({self.role})"

class CompanyInvitation(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='accounts_invitations')
    invited_email = models.EmailField()
    invited_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='accounts_invitations_sent')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='member')
    token = models.CharField(max_length=100, unique=True, default=secrets.token_hex)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'invited_email')
        indexes = [models.Index(fields=['token']), models.Index(fields=['invited_email'])]

    def __str__(self):
        return f"Invitation to {self.invited_email} for {self.company.name}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=INVITATION_EXPIRY_DAYS)
        super().save(*args, **kwargs)

class CompanyDocument(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='accounts_documents')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='accounts_uploaded_documents')
    name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    category = models.CharField(max_length=50, choices=DOCUMENT_CATEGORY_CHOICES, blank=True)
    file = models.FileField(upload_to='company_documents/%Y/%m/')
    expiry_date = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['company', 'document_type']), models.Index(fields=['expiry_date'])]

    def __str__(self):
        return f"{self.name} ({self.get_document_type_display()}) for {self.company.name}"

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            self.expiry_date = timezone.now().date() + timedelta(days=DEFAULT_DOCUMENT_EXPIRY_DAYS)
        super().save(*args, **kwargs)

    @property
    def days_to_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.now().date()).days

    def is_expiring_soon(self):
        days = self.days_to_expiry
        return days is not None and days <= DOCUMENT_EXPIRY_NOTIFICATION_DAYS

class CompanyOffice(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='accounts_offices')
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    is_headquarters = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'name')
        indexes = [models.Index(fields=['company', 'city'])]

    def __str__(self):
        return f"{self.name} Office - {self.company.name}"

class CompanyCertification(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='accounts_certifications')
    name = models.CharField(max_length=255)
    issuing_authority = models.CharField(max_length=255)
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    certificate_number = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to='company_certifications/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['company', 'name'])]

    def __str__(self):
        return f"{self.name} for {self.company.name}"

class CompanyAnnualTurnover(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='accounts_annual_turnovers'
    )
    year = models.PositiveIntegerField(validators=[MinValueValidator(1900), MaxValueValidator(timezone.now().year)])
    amount = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=10, default='USD')
    proof = models.FileField(upload_to='company_turnovers/%Y/%m/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'year')
        ordering = ['-year']
        indexes = [models.Index(fields=['company', 'year'])]

    def __str__(self):
        return f"{self.company.name} - Turnover {self.year}: {self.amount} {self.currency}"

class CompanyLitigation(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='accounts_litigations'
    )
    case_number = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=[('pending', 'Pending'), ('resolved', 'Resolved'), ('dismissed', 'Dismissed')])
    filed_date = models.DateField()
    resolution_date = models.DateField(blank=True, null=True)
    outcome = models.TextField(blank=True)
    amount_involved = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True)
    currency = models.CharField(max_length=10, default='USD', blank=True)
    proof = models.FileField(upload_to='company_litigations/%Y/%m/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-filed_date']
        indexes = [models.Index(fields=['company', 'case_number'])]

    def __str__(self):
        return f"{self.company.name} - Litigation {self.case_number}"

class CompanyPersonnel(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='accounts_personnel'
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    position = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    qualifications = models.TextField(blank=True)
    education_level = models.CharField(
        max_length=20,
        choices=[
            ('certificate', 'Certificate'),
            ('diploma', 'Diploma'),
            ('bachelor', "Bachelor's Degree"),
            ('master', "Master's Degree"),
            ('phd', 'PhD'),
        ],
        blank=True
    )
    age = models.PositiveIntegerField(blank=True, null=True, validators=[MinValueValidator(0)])
    nationality = models.CharField(max_length=100, blank=True)
    professional_certifications = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    resume = models.FileField(upload_to='company_personnel/%Y/%m/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [models.Index(fields=['company', 'position'])]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.position} at {self.company.name}"

class CompanyFinancialStatement(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='accounts_financial_statements'
    )
    year = models.PositiveIntegerField(validators=[MinValueValidator(1900), MaxValueValidator(timezone.now().year)])
    total_assets = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00)
    total_liabilities = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00)
    total_equity = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00)
    gross_profit = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00)
    profit_before_tax = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00)
    current_assets = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00)
    current_liabilities = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00)
    cash_and_bank = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00)
    total_revenue = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00)
    audit_report = models.FileField(upload_to='company_audit_reports/%Y/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'year')
        ordering = ['-year']
        indexes = [models.Index(fields=['company', 'year'])]

    def __str__(self):
        return f"{self.company.name} - Financials {self.year}"

    @property
    def current_ratio(self):
        if self.current_liabilities == 0:
            return 0
        return self.current_assets / self.current_liabilities

    @property
    def cash_ratio(self):
        if self.current_liabilities == 0:
            return 0
        return self.cash_and_bank / self.current_liabilities

    @property
    def working_capital(self):
        return self.current_assets - self.current_liabilities

    @property
    def gross_profit_margin(self):
        if self.total_revenue == 0:
            return 0
        return (self.gross_profit / self.total_revenue) * 100

    @property
    def debt_to_equity_ratio(self):
        if self.total_equity == 0:
            return 0
        return self.total_liabilities / self.total_equity

    @property
    def return_on_assets(self):
        if self.total_assets == 0:
            return 0
        return (self.profit_before_tax / self.total_assets) * 100

class CompanySourceOfFund(models.Model):
    SOURCE_CHOICES = [
        ('government', 'Government Funds'),
        ('loan', 'Loan'),
        ('credit', 'Credit'),
        ('grant', 'Grant'),
        ('other', 'Other'),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='accounts_sources_of_funds'
    )
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    amount = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=10)
    proof = models.FileField(upload_to='company_sources_of_fund/%Y/%m/', help_text='Upload proof of funds document')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Company Source of Fund"
        verbose_name_plural = "Company Sources of Funds"
        ordering = ['-uploaded_at']
        indexes = [models.Index(fields=['company', 'source_type'])]

    def __str__(self):
        return f"{self.company.name} – {self.get_source_type_display()}: {self.amount} {self.currency}"

class CompanyExperience(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='accounts_experiences'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    contract_count = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    total_value = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=10, default='USD')
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    client_name = models.CharField(max_length=255, blank=True)
    proof = models.FileField(upload_to='company_experiences/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'title')
        ordering = ['-start_date']
        indexes = [models.Index(fields=['company', 'title'])]

    def __str__(self):
        return f"{self.company.name} - Experience {self.title}"

class AuditLog(models.Model):
    action = models.CharField(max_length=50)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='accounts_audit_logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField()
    class Meta:
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['action', 'timestamp']), models.Index(fields=['user'])]

    def __str__(self):
        return f"{self.action} - {self.timestamp}"