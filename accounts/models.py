import uuid
import secrets
from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
    Group,
    Permission
)
from django.db.models import Avg
from django.core.validators import MinValueValidator, MaxValueValidator
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
    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="companies"
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
        choices=[('active','Active'),('inactive','Inactive'),('suspended','Suspended')],
        default='active'
    )
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
        CustomUser, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_companies'
    )

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name','slug']),
            models.Index(fields=['owner']),
            models.Index(fields=['deleted_at']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        existing = self.owner.companies.filter(deleted_at__isnull=True).exclude(id=self.id).count()
        if existing >= MAX_COMPANIES_PER_USER:
            raise ValidationError(f"A user can only own {MAX_COMPANIES_PER_USER} company.")

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.full_clean()
            if not self.slug:
                self.slug = slugify(self.name)
            super().save(*args, **kwargs)
            # ensure owner is CompanyUser
            if not self.company_users.filter(user=self.owner).exists():
                CompanyUser.objects.create(company=self, user=self.owner, role='owner')

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.status = 'inactive'
        self.save()

    def verify(self, user):
        self.is_verified = True
        self.verification_date = timezone.now()
        self.save(update_fields=['is_verified','verification_date'])
        AuditLog.objects.create(
            action='company_verified',
            user=user,
            details={'company_id':str(self.id),'company_name':self.name}
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
        unique_together = ('company','user')

    def clean(self):
        original = CompanyUser.objects.filter(pk=self.pk).first()
        if original and original.role=='owner' and self.role!='owner':
            raise ValidationError("Cannot change owner's role.")
        if self.role=='owner':
            owners = self.company.company_users.filter(role='owner')
            if self.pk:
                owners=owners.exclude(pk=self.pk)
            if owners.exists():
                raise ValidationError("A company can only have one owner.")
        if self._state.adding:
            count = self.company.company_users.count()
            if count>=MAX_COMPANY_USERS:
                raise ValidationError(f"A company can only have up to {MAX_COMPANY_USERS} members.")

    def save(self,*args,**kwargs):
        self.full_clean()
        super().save(*args,**kwargs)


class CompanyInvitation(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='invitations'
    )
    invited_email = models.EmailField()
    invited_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='sent_invitations'
    )
    role = models.CharField(max_length=20,choices=ROLE_CHOICES)
    token = models.CharField(max_length=64,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True,null=True)
    accepted = models.BooleanField(default=False)

    class Meta:
        ordering=['-created_at']
        indexes=[models.Index(fields=['token'])]

    def save(self,*args,**kwargs):
        if not self.token:
            self.token=secrets.token_urlsafe(48)
        if not self.expires_at:
            self.expires_at=timezone.now()+timedelta(days=INVITATION_EXPIRY_DAYS)
        super().save(*args,**kwargs)


class CompanyOffice(models.Model):
    company = models.ForeignKey(Company,on_delete=models.CASCADE,related_name='offices')
    uuid = models.UUIDField(default=uuid.uuid4,unique=True)
    director_title = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    physical_address = models.TextField()
    postal_address = models.CharField(max_length=50)
    region = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    council = models.CharField(max_length=100)
    ward = models.CharField(max_length=100)
    street = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.company.name} office ({self.director_title})"


class CompanyCertification(models.Model):
    AWARD='award';CERTIFICATION='certification';LICENSE='license'
    TIN='tin';TAX='tax';BLERA='blera';OSHA='osha';OTHER='other'
    TYPE_CHOICES=[(AWARD,'Award'),(CERTIFICATION,'Certification'),
                  (LICENSE,'License'),(TIN,'TIN'),(TAX,'TAX'),
                  (BLERA,'Blera'),(OSHA,'OSHA'),(OTHER,'Other')]
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name='certifications')
    cert_type=models.CharField(max_length=20,choices=TYPE_CHOICES)
    name=models.CharField(max_length=255,blank=True)
    file=models.FileField(upload_to='company_certifications/%Y/%m/')
    issued_date=models.DateField(blank=True,null=True)
    expiry_date=models.DateField(blank=True,null=True)
    notes=models.TextField(blank=True)
    class Meta:
        ordering=['company','cert_type']
    def __str__(self):
        return f"{self.company.name} - {self.get_cert_type_display()}"


class CompanyDocument(models.Model):
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name='documents')
    uploaded_by=models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    document_type=models.CharField(max_length=50,choices=DOCUMENT_TYPE_CHOICES)
    document_category=models.CharField(max_length=50,choices=DOCUMENT_CATEGORY_CHOICES,default='other')
    document_file=models.FileField(upload_to='company_documents/')
    uploaded_at=models.DateTimeField(auto_now_add=True)
    expires_at=models.DateTimeField(blank=True,null=True)
    is_expired=models.BooleanField(default=False)
    status=models.CharField(max_length=20,choices=[('Approved','Approved'),('Denied','Denied'),('Under Review','Under Review')],default='Under Review')
    notification_sent=models.JSONField(default=dict,blank=True)
    notification_attempts=models.JSONField(default=dict,blank=True)
    class Meta:
        ordering=['-uploaded_at']
        indexes=[models.Index(fields=['expires_at']),models.Index(fields=['is_expired']),models.Index(fields=['document_category']),models.Index(fields=['uploaded_at'])]
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.document_file.name}"
    def clean(self):
        if self.uploaded_by!=self.company.owner:
            raise ValidationError("Only company owners can upload documents.")
        if self.expires_at and self.expires_at<timezone.now():
            raise ValidationError("Expiration date cannot be in the past.")
    def reset_notifications(self):
        threshold=timezone.now()+timedelta(days=DOCUMENT_EXPIRY_NOTIFICATION_DAYS)
        if self.expires_at and self.expires_at>threshold:
            self.notification_sent={};self.notification_attempts={}
    def save(self,*args,**kwargs):
        if not self.expires_at:
            self.expires_at=timezone.now()+timedelta(days=DEFAULT_DOCUMENT_EXPIRY_DAYS)
        self.is_expired=self.expires_at<timezone.now()
        self.reset_notifications()
        self.full_clean()
        super().save(*args,**kwargs)

class CompanyLitigation(models.Model):
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name='litigations')
    title=models.CharField(max_length=255)
    description=models.TextField(blank=True)
    start_date=models.DateField()
    end_date=models.DateField(blank=True,null=True)
    status=models.CharField(max_length=50,choices=[('open','Open'),('closed','Closed'),('settled','Settled')])
    def __str__(self):
        return f"{self.company.name} - {self.title} ({self.status})"

class CompanyPersonnel(models.Model):
    EMPLOYEE_TYPE_CHOICES = [
        ('employee', 'Employee'),
        ('expert',   'Expert'),
    ]

    GENDER_CHOICES = [
        ('male',   'Male'),
        ('female', 'Female'),
        ('other',  'Other'),
    ]

    company          = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name='personnel'
    )
    uuid             = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Name components
    first_name       = models.CharField(max_length=50, default='')
    middle_name      = models.CharField(max_length=50, blank=True, default='')
    last_name        = models.CharField(max_length=50, default='')

    # Personal info
    gender           = models.CharField(max_length=10, choices=GENDER_CHOICES, default='other')
    date_of_birth    = models.DateField(default=timezone.now)
    phone_number     = models.CharField(max_length=20, default='')
    email            = models.EmailField(default='')
    physical_address = models.TextField(default='')

    # Employment details
    employee_type      = models.CharField(max_length=10, choices=EMPLOYEE_TYPE_CHOICES, default='employee')
    job_title          = models.CharField(max_length=100, default='')
    date_of_employment = models.DateField(default=timezone.now)
    language_spoken    = models.CharField(max_length=200, default='', help_text='Comma-separated list of languages')

    # Verification
    is_verified        = models.BooleanField(default=False)
    verified_at        = models.DateTimeField(null=True, blank=True, default=None)

    # Legacy / optional
    education          = models.CharField(max_length=200, blank=True, default='')
    years_experience   = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    professional_registration = models.BooleanField(default=False)

    # Timestamps with defaults so migrations won’t prompt
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['last_name', 'first_name']
        unique_together = [('company', 'uuid')]

    def __str__(self):
        return f"{self.company.name} – {self.first_name} {self.last_name} ({self.job_title})"

    def verify(self):
        """Mark this personnel as verified now."""
        if not self.is_verified:
            self.is_verified = True
            self.verified_at = timezone.now()
            self.save(update_fields=['is_verified', 'verified_at'])

class CompanyAnnualTurnover(models.Model):
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name='annual_turnovers')
    year=models.PositiveIntegerField()
    currency=models.CharField(max_length=10)
    amount=models.DecimalField(max_digits=20,decimal_places=2,validators=[MinValueValidator(0)])
    class Meta:
        unique_together=('company','year')
        ordering=['-year']
    def __str__(self):
        return f"{self.company.name} - {self.year}: {self.amount} {self.currency}"

class CompanyFinancialStatement(models.Model):
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name='financial_statements')
    year=models.PositiveIntegerField()
    currency=models.CharField(max_length=10)
    total_assets=models.DecimalField(max_digits=20,decimal_places=2,validators=[MinValueValidator(0)])
    total_liabilities=models.DecimalField(max_digits=20,decimal_places=2,validators=[MinValueValidator(0)])
    total_equity=models.DecimalField(max_digits=20,decimal_places=2,validators=[MinValueValidator(0)])
    gross_profit=models.DecimalField(max_digits=20,decimal_places=2,validators=[MinValueValidator(0)])
    profit_before_tax=models.DecimalField(max_digits=20,decimal_places=2)
    cash_flow=models.DecimalField(max_digits=20,decimal_places=2)
    file=models.FileField(upload_to='company_financials/%Y/')
    audit_report=models.FileField(upload_to='company_audit_reports/%Y/',blank=True,null=True)
    uploaded_at=models.DateTimeField(auto_now_add=True)

    # New fields for ratio calculations
    current_assets = models.DecimalField(
        max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00
    )
    current_liabilities = models.DecimalField(
        max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00
    )
    cash_and_bank = models.DecimalField(
        max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00
    )
    total_revenue = models.DecimalField(
        max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], default=0.00
    )

    class Meta:
        unique_together=('company','year')
        ordering=['-year']
    def __str__(self):
        return f"{self.company.name} - Financials {self.year}"

    # Calculated ratios as properties
    @property
    def current_ratio(self):
        """Current Ratio: Current Assets (CA) / Current Liabilities (CL). Example min: 1"""
        if self.current_liabilities == 0:
            return 0
        return self.current_assets / self.current_liabilities

    @property
    def cash_ratio(self):
        """Cash Ratio: Cash and Bank (C&B) / Current Liabilities (CL). Example min: N/A (optional)"""
        if self.current_liabilities == 0:
            return 0
        return self.cash_and_bank / self.current_liabilities

    @property
    def working_capital(self):
        """Working Capital: Current Assets (CA) - Current Liabilities (CL). Example min: 1"""
        return self.current_assets - self.current_liabilities

    @property
    def gross_profit_margin(self):
        """Gross Profit Margin: (Gross Profit (GP) / Total Revenue (TR)) * 100. Example min: 10"""
        if self.total_revenue == 0:
            return 0
        return (self.gross_profit / self.total_revenue) * 100

    @property
    def debt_to_equity_ratio(self):
        """Debt to Equity Ratio: Total Liabilities (TL) / Total Equity (TE). Example min: 1"""
        if self.total_equity == 0:
            return 0
        return self.total_liabilities / self.total_equity

    @property
    def return_on_assets(self):
        """Return on Assets: (Profit before Tax (PBT) / Total Assets (TA)) * 100. Example min: 5"""
        if self.total_assets == 0:
            return 0
        return (self.profit_before_tax / self.total_assets) * 100
    
class CompanySourceOfFund(models.Model):
    CASH_AND_BANK = 'cash_and_bank'
    GRANT = 'grant'
    INVENTORIES = 'inventories'
    SOURCE_CHOICES = [
        (CASH_AND_BANK, 'Cash and Bank'),
        (GRANT, 'Grant'),
        (INVENTORIES, 'Inventories'),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='sources_of_funds'
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=10)
    proof = models.FileField(
        upload_to='company_sources_of_fund/%Y/%m/',
        help_text='Upload proof of funds document'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Company Source of Fund"
        verbose_name_plural = "Company Sources of Funds"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.company.name} – {self.get_source_type_display()}: {self.amount} {self.currency}"

class AuditLog(models.Model):
    action=models.CharField(max_length=50)
    user=models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,related_name='accounts_audit_logs')
    timestamp=models.DateTimeField(auto_now_add=True)
    details=models.JSONField()
    class Meta:
        ordering=['-timestamp']
        indexes=[models.Index(fields=['action','timestamp']),models.Index(fields=['user'])]
    def __str__(self):
        return f"{self.action} - {self.timestamp}"