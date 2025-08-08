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
    tender_type_country = models.CharField(max_length=30, choices=TenderTypeCountry)
    tender_type_sector = models.CharField(max_length=50, choices=TenderTypeSector)
    currency = models.CharField(max_length=3, choices=CurrencyTYpes, default='TZS')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True)
    procurement_process = models.ForeignKey(ProcurementProcess, on_delete=models.SET_NULL, null=True, blank=True)
    agency = models.ForeignKey(AgencyDetails, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    publication_date = models.DateTimeField(null=True, blank=True)
    submission_deadline = models.DateTimeField()
    clarification_deadline = models.DateTimeField(null=True, blank=True)
    evaluation_start_date = models.DateTimeField(null=True, blank=True)
    evaluation_end_date = models.DateTimeField(null=True, blank=True)
    validity_period_days = models.PositiveIntegerField(default=90)
    completion_period_days = models.PositiveIntegerField(null=True, blank=True)  # Used for delivery period
    litigation_history_start = models.DateField(null=True, blank=True)
    litigation_history_end = models.DateField(null=True, blank=True)
    tender_document = models.FileField(upload_to='tender_docs/%Y/%m/', blank=True, null=True)
    tender_fees = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tender_securing_type = models.CharField(max_length=30, choices=TenderSecurityType, default="Tender Securing Declaration")
    tender_security_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tender_security_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    tender_security_currency = models.CharField(max_length=3, choices=CurrencyTYpes, default='TZS')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    last_status_change = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_tenders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # NEW: Flag for allowing alternative delivery schedules
    allow_alternative_delivery = models.BooleanField(default=False, help_text="Whether bidders can propose alternative delivery schedules")

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['slug', 'status'])]

    def __str__(self):
        return f"{self.reference_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.reference_number}-{self.title}")
            self.slug = base_slug
            counter = 1
            while Tender.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        if self.status == 'published' and not self.publication_date:
            self.publication_date = timezone.now()
        super().save(*args, **kwargs)

    def send_notification_emails(self):
        subscriptions = TenderSubscription.objects.filter(category=self.category)
        for sub in subscriptions:
            user = sub.user
            prefs = NotificationPreference.objects.get_or_create(user=user)[0]
            if prefs.email_notifications:
                html_message = render_to_string('emails/new_tender.html', {'tender': self, 'user': user})
                send_mail(
                    subject=f'New Tender Published: {self.title}',
                    message='',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=True
                )
                TenderNotification.objects.create(subscription=sub, tender=self, sent_at=timezone.now(), is_sent=True)


# NEW: Model for detailed technical specifications conformance
class TenderTechnicalSpecification(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='technical_specifications')
    category = models.CharField(max_length=100, choices=[
        ('service', 'Service Specifications'),
        ('technology', 'Technology Specifications'),
        ('security', 'Security Specifications'),
        ('architecture', 'Technical Architecture'),
        ('usability', 'Usability'),
        ('testing', 'Testing and Quality Assurance'),
        ('conformity', 'Conformity to Technical Requirements'),
    ])
    description = models.TextField(blank=True)
    complied = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_category_display()} for {self.tender.reference_number}"


class TenderRequiredDocument(models.Model):
    DOCUMENT_TYPES = (
        ('legal', 'Legal'),
        ('financial', 'Financial'),
        ('technical', 'Technical'),
        ('other', 'Other'),
    )
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='required_documents')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other')

    def __str__(self):
        return f"{self.name} for {self.tender.reference_number}"


class TenderFinancialRequirement(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='financial_requirements')
    name = models.CharField(max_length=100)
    formula = models.CharField(max_length=200, blank=True)
    minimum = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    actual_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    complied = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    # NEW: Period for financial ratios/statements
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # NEW: JV compliance rules
    JV_COMPLIANCE_CHOICES = (
        ('combined', 'All Parties Combined Must Meet'),
        ('each', 'Each Member Must Meet'),
        ('one', 'One Member Must Meet'),
        ('custom', 'Custom'),
    )
    jv_compliance = models.CharField(max_length=20, choices=JV_COMPLIANCE_CHOICES, default='combined', blank=True)
    jv_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Percentage for each/one member if applicable")

    def __str__(self):
        return f"{self.name} for {self.tender.reference_number}"

    def evaluate(self, value=None):
        v = value if value is not None else self.actual_value
        self.complied = v >= self.minimum if self.minimum else True
        self.save()
        return self.complied


class TenderTurnoverRequirement(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='turnover_requirements')
    label = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Tender.CurrencyTYpes, default='TZS')
    start_date = models.DateField()
    end_date = models.DateField()
    complied = models.BooleanField(default=False)

    # NEW: JV compliance rules (similar to above)
    jv_compliance = models.CharField(max_length=20, choices=TenderFinancialRequirement.JV_COMPLIANCE_CHOICES, default='combined', blank=True)
    jv_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])

    def __str__(self):
        return f"{self.label} for {self.tender.reference_number}"


class TenderExperienceRequirement(models.Model):
    EXPERIENCE_TYPES = (
        ('general', 'General Experience'),
        ('specific', 'Specific Experience'),
        ('contract_management', 'Contract Management Experience'),
    )
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='experience_requirements')
    type = models.CharField(max_length=20, choices=EXPERIENCE_TYPES)
    description = models.TextField()
    contract_count = models.PositiveIntegerField()
    min_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=Tender.CurrencyTYpes, default='TZS', blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    complied = models.BooleanField(default=False)

    # NEW: JV compliance rules
    jv_compliance = models.CharField(max_length=20, choices=TenderFinancialRequirement.JV_COMPLIANCE_CHOICES, default='combined', blank=True)
    jv_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    jv_aggregation_note = models.TextField(blank=True, help_text="Notes on aggregation for JV, e.g., no aggregation for value")

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

    # NEW: JV compliance (if applicable for personnel)
    jv_compliance = models.CharField(max_length=20, choices=TenderFinancialRequirement.JV_COMPLIANCE_CHOICES, default='combined', blank=True)

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