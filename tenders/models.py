from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from accounts.models import CustomUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = "Industry Category"
        verbose_name_plural = "Industry Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

class SubCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Industry Sub Category"
        verbose_name_plural = "Industry Sub Categories"
        unique_together = ('category', 'slug')
        ordering = ['name']

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while SubCategory.objects.filter(category=self.category, slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

class AgencyDetails(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='agency_logos/%Y/%m/', blank=True, null=True)
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agency"
        verbose_name_plural = "Agencies"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while AgencyDetails.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class ProcurementProcess(models.Model):
    PROCESS_TYPES = (
        ('open', 'Open Tendering'),
        ('selective', 'Selective Tendering'),
        ('limited', 'Limited Tendering'),
        ('direct', 'Direct Procurement'),
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    type = models.CharField(max_length=20, choices=PROCESS_TYPES)
    description = models.TextField()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while ProcurementProcess.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class Tender(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("pending", "Pending Approval"),
        ("published", "Published"),
        ("evaluation", "Under Evaluation"),
        ("awarded", "Awarded"),
        ("closed", "Closed"),
        ("canceled", "Canceled"),
    )
    CurrencyTYpes = (
        ('TZS', 'Tanzanian Shilling'),
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('JPY', 'Japanese Yen'),
        ('CNY', 'Chinese Yuan'),
    )  
    TenderTypeCountry = (
        ('National', 'National Tendering'),
        ('International', 'International Tendering'),
    )
    TenderTypeSector = (
        ('Private Company', 'Private Company Tendering'),
        ('Public Sector', 'Public Sector Tendering'),
        ('Non-Governmental Organization', 'Non-Governmental Organization Tendering'),
        ('Government Agency', 'Government Agency Tendering'),
    )
    TenderSecurityType = (
        ("Tender Security", "Tender Security"),
        ("Tender Securing Declaration", "Tender Securing Declaration"),
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    reference_number = models.CharField(max_length=50, unique=True)
    tender_type_country = models.CharField(max_length=30, choices=TenderTypeCountry, default='National')
    tender_type_sector = models.CharField(max_length=30, choices=TenderTypeSector, default='Private Company')
    tenderdescription = models.TextField(default="tender description to be updated")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True)
    procurement_process = models.ForeignKey(ProcurementProcess, on_delete=models.SET_NULL, null=True)
    agency = models.ForeignKey(AgencyDetails, on_delete=models.SET_NULL, null=True, related_name='tenders')

    publication_date = models.DateTimeField(default=timezone.now)
    submission_deadline = models.DateTimeField()
    clarification_deadline = models.DateTimeField()
    evaluation_start_date = models.DateTimeField(null=True, blank=True)
    evaluation_end_date = models.DateTimeField(null=True, blank=True)

    validity_period_days = models.PositiveIntegerField(null=True, blank=True)
    completion_period_days = models.PositiveIntegerField(null=True, blank=True)
    litigation_history_start = models.DateField(null=True, blank=True)
    litigation_history_end = models.DateField(null=True, blank=True)
    tender_document= models.FileField(upload_to='tender_documents/%Y/%m/', blank=True, null=True)
    tender_fees = models.DecimalField(max_digits=16, decimal_places=2)
    tender_securing_type = models.CharField(max_length=30, default='Tender Security', choices=TenderSecurityType)
    tender_security_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        blank=True, null=True
    )
    tender_security_amount = models.DecimalField(
        max_digits=16, decimal_places=2,
        validators=[MinValueValidator(0)], blank=True, null=True
    )
    tender_security_currency = models.CharField(max_length=10, default='TZS',choices=CurrencyTYpes)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_tenders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    last_status_change = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(fields=['-publication_date']),
            models.Index(fields=['status']),
            models.Index(fields=['slug']),
        ]
        ordering = ['-publication_date']

    def __str__(self):
        return f"{self.reference_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Tender.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    # Helper methods
    def is_active(self):
        return self.status in ['published', 'evaluation']

    def time_to_submission(self):
        return (self.submission_deadline - timezone.now()).days

    def compliance_summary(self):
        summary = {}
        for req in self.financial_requirements.all():
            summary[req.name] = req.complied
        for req in self.turnover_requirements.all():
            summary[req.label] = req.complied
        for req in self.experience_requirements.all():
            summary[f"Experience {req.type}"] = req.complied
        for req in self.personnel_requirements.all():
            summary[f"Personnel {req.role}"] = req.complied
        return summary

    def get_required_documents(self):
        return self.required_documents.all()

    def subscribe(self, user, keywords=None):
        from .models import TenderSubscription
        criteria = {
            'category': self.category,
            'subcategory': self.subcategory,
            'procurement_process': self.procurement_process,
            'keywords': keywords or ''
        }
        subscription, created = TenderSubscription.objects.get_or_create(user=user, defaults=criteria)
        return subscription

    def send_notification_emails(self):
        from django.db.models import Q
        from .models import TenderSubscription, TenderNotification
        for sub in TenderSubscription.objects.filter(is_active=True).filter(
            Q(category=self.category) | Q(category__isnull=True),
            Q(subcategory=self.subcategory) | Q(subcategory__isnull=True),
            Q(procurement_process=self.procurement_process) | Q(procurement_process__isnull=True)
        ):
            content = f"{self.title} {self.tenderdescription}".lower()
            if sub.keywords:
                keywords = [k.strip().lower() for k in sub.keywords.split(',')]
                if not any(kw in content for kw in keywords):
                    continue
            pref = getattr(sub.user, 'notification_preference', None)
            if pref and not pref.email_notifications:
                continue
            notif, created = TenderNotification.objects.get_or_create(
                subscription=sub,
                tender=self,
                defaults={'is_sent': False}
            )
            if not notif.is_sent:
                send_notification_email(notif)


class TenderRequiredDocument(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='required_documents')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    document_type = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.name} for {self.tender.title}"


class TenderFinancialRequirement(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='financial_requirements')
    name = models.CharField(max_length=100)
    formula = models.CharField(max_length=255)
    minimum = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=50, blank=True)
    actual_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    complied = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.tender.reference_number})"

    def evaluate(self, value=None):
        val = value if value is not None else self.actual_value
        self.complied = val is not None and val >= self.minimum
        self.save()
        return self.complied


class TenderTurnoverRequirement(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='turnover_requirements')
    label = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=10, default='TZS')
    start_date = models.DateField()
    end_date = models.DateField()
    complied = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.label} for {self.tender.reference_number}"

    def evaluate(self, reported_amount):
        self.complied = reported_amount >= self.amount
        self.save()
        return self.complied


class TenderExperienceRequirement(models.Model):
    SPECIFIC = 'specific'
    GENERAL = 'general'
    TYPE_CHOICES = (
        (SPECIFIC, 'Specific'),
        (GENERAL, 'General'),
    )
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='experience_requirements')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField()
    contract_count = models.PositiveIntegerField()
    min_value = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=10, default='TZS')
    start_date = models.DateField()
    end_date = models.DateField()
    complied = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_type_display()} experience for {self.tender.reference_number}"

    def evaluate(self, count=None, value=None):
        c = count if count is not None else self.contract_count
        v = value if value is not None else self.min_value
        self.complied = c >= self.contract_count and v >= self.min_value
        self.save()
        return self.complied


class TenderPersonnelRequirement(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='personnel_requirements')
    role = models.CharField(max_length=100)
    min_education = models.CharField(max_length=100)
    professional_registration = models.BooleanField(default=False)
    min_experience_yrs = models.PositiveIntegerField()
    appointment_duration_years = models.PositiveIntegerField()
    nationality_required = models.CharField(max_length=50, blank=True)
    language_required = models.CharField(max_length=100, blank=True)
    complied = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.role} for {self.tender.reference_number}"

    def evaluate(self, years_of_experience):
        self.complied = years_of_experience >= self.min_experience_yrs
        self.save()
        return self.complied


class TenderScheduleItem(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='schedule_items')
    commodity = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField()
    specification = models.TextField(blank=True)

    def __str__(self):
        return f"{self.commodity} for {self.tender.reference_number}"


class TenderSubscription(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tender_subscriptions')
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, null=True, blank=True)
    procurement_process = models.ForeignKey(ProcurementProcess, on_delete=models.CASCADE, null=True, blank=True)
    keywords = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'category', 'subcategory', 'procurement_process')]
        indexes = [models.Index(fields=['user', 'is_active']), models.Index(fields=['slug'])]

    def __str__(self):
        parts = []
        if self.category: parts.append(self.category.name)
        if self.subcategory: parts.append(self.subcategory.name)
        if self.procurement_process: parts.append(self.procurement_process.name)
        if self.keywords: parts.append(self.keywords)
        return f"Subscription: {' | '.join(parts)}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = '-'.join(filter(None,[self.user.email, self.category.name if self.category else '',
                                        self.subcategory.name if self.subcategory else '', self.procurement_process.name if self.procurement_process else '',
                                        self.keywords.replace(',', '-')]))[:190]
            self.slug = slugify(base)
        super().save(*args, **kwargs)


class NotificationPreference(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_preference')
    email_notifications = models.BooleanField(default=True)
    notification_frequency = models.CharField(max_length=20, choices=[('immediate','Immediate'),('daily','Daily'),('weekly','Weekly')], default='immediate')
    last_notified = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prefs for {self.user.email}"


class TenderNotification(models.Model):
    subscription = models.ForeignKey(TenderSubscription, on_delete=models.CASCADE, related_name='notifications')
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='notifications')
    sent_at = models.DateTimeField(null=True, blank=True)
    is_sent = models.BooleanField(default=False)
    delivery_status = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('subscription','tender')]

    def __str__(self):
        return f"Notification to {self.subscription.user.email} for {self.tender.reference_number}"


class TenderStatusHistory(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=Tender.STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.tender.reference_number} -> {self.status} at {self.changed_at}"


# Signals for notifications
@receiver(post_save, sender=Tender)
def create_tender_notifications(sender, instance, created, **kwargs):
    if instance.status == 'published':
        instance.send_notification_emails()
