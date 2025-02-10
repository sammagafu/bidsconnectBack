from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.auth.models import Group, Permission


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
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="customuser_set",  # Unique related_name
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="customuser_set",  # Unique related_name
        related_query_name="customuser",
    )


    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

class Company(models.Model):
    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="companies"
    )
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    # ... other fields ...

    def clean(self):
        if self.owner.companies.exclude(id=self.id).count() >= 3:
            raise ValidationError("Maximum of 3 companies per user allowed.")

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            num = 1
            while Company.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{num}"
                num += 1
            self.slug = unique_slug
        
        super().save(*args, **kwargs)
        
        # Automatically create CompanyUser for owner
        if not self.company_users.filter(user=self.owner).exists():
            CompanyUser.objects.create(
                company=self,
                user=self.owner,
                role='owner'
            )

class CompanyUser(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('user', 'User'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'user')

    def clean(self):
        # Prevent role changes for owners
        original = CompanyUser.objects.filter(pk=self.pk).first()
        if original and original.role == 'owner' and self.role != 'owner':
            raise ValidationError("Cannot change owner's role.")
            
        # Enforce single owner per company
        if self.role == 'owner' and self.company.company_users.filter(role='owner').exists():
            raise ValidationError("A company can only have one owner.")

        # User limit validation
        existing_count = self.company.company_users.count()
        if self.pk is None and existing_count >= 5:
            raise ValidationError("Maximum of 5 users per company.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

class CompanyInvitation(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    invited_email = models.EmailField()
    invited_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=CompanyUser.ROLE_CHOICES)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = get_random_string(length=64)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=3)
        super().save(*args, **kwargs)

class CompanyDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        # ... choices ...
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50)
    document_file = models.FileField(upload_to='company_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.company.owner != self._state.user:
            raise ValidationError("Only company owners can upload documents.")