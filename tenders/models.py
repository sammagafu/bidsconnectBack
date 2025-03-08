from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser
from django.utils.text import slugify
from django.core.exceptions import ValidationError

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure slug uniqueness
            counter = 1
            while Category.objects.filter(slug=self.slug).exists():
                self.slug = f"{slugify(self.name)}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

class SubCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('category', 'slug')
        ordering = ['name']

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            # Ensure slug uniqueness within the same category
            counter = 1
            while SubCategory.objects.filter(category=self.category, slug=self.slug).exists():
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
    type = models.CharField(max_length=20, choices=PROCESS_TYPES)
    description = models.TextField()

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"

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
    
    # Core Information
    title = models.CharField(max_length=200)
    reference_number = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    procurement_process = models.ForeignKey(ProcurementProcess, on_delete=models.SET_NULL, null=True)
    
    # Timeline
    publication_date = models.DateTimeField(default=timezone.now)
    submission_deadline = models.DateTimeField()
    clarification_deadline = models.DateTimeField()
    evaluation_start_date = models.DateTimeField(null=True, blank=True)
    evaluation_end_date = models.DateTimeField(null=True, blank=True)
    
    # Financials
    estimated_budget = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3, default='TSH')
    bid_bond_percentage = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Location
    address = models.TextField()
    # Relationships
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_tenders')
    evaluation_committee = models.ManyToManyField(CustomUser, related_name='evaluation_tenders', blank=True)
    
    # Status Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    last_status_change = models.DateTimeField(auto_now=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(fields=['-publication_date']),
            models.Index(fields=['status']),
        ]
        ordering = ['-publication_date']

    def __str__(self):
        return f"{self.reference_number} - {self.title}"

class TenderDocument(models.Model):
    DOCUMENT_TYPES = (
        ('notice', 'Tender Notice'),
        ('technical', 'Technical Specifications'),
        ('financial', 'Financial Requirements'),
        ('evaluation', 'Evaluation Criteria'),
        ('contract', 'Draft Contract'),
    )
    
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='tender_documents/%Y/%m/')
    version = models.CharField(max_length=10)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tender', 'document_type', 'version')

class Bid(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('qualified', 'Technically Qualified'),
        ('disqualified', 'Disqualified'),
        ('awarded', 'Awarded'),
        ('withdrawn', 'Withdrawn'),
    )
    
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='bids')
    bidder = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='submitted_bids')
    
    # Pricing
    total_price = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    validity_days = models.PositiveIntegerField(default=90)
    
    # Evaluation
    technical_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    financial_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    combined_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submission_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('tender', 'bidder')
        ordering = ['-submission_date']

class BidDocument(models.Model):
    DOCUMENT_TYPES = (
        ('technical', 'Technical Proposal'),
        ('financial', 'Financial Proposal'),
        ('qualification', 'Qualification Documents'),
        ('bid_bond', 'Bid Bond'),
    )
    
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='bid_documents/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class EvaluationCriterion(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='evaluation_criteria')
    name = models.CharField(max_length=200)
    description = models.TextField()
    weight = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_score = models.DecimalField(max_digits=5, decimal_places=2)

class EvaluationResponse(models.Model):
    criterion = models.ForeignKey(EvaluationCriterion, on_delete=models.CASCADE)
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='evaluations')
    score = models.DecimalField(max_digits=5, decimal_places=2)
    comments = models.TextField(blank=True)
    evaluated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

class Contract(models.Model):
    tender = models.OneToOneField(Tender, on_delete=models.CASCADE, related_name='contract')
    bid = models.OneToOneField(Bid, on_delete=models.CASCADE, related_name='awarded_contract')
    start_date = models.DateField()
    end_date = models.DateField()
    value = models.DecimalField(max_digits=16, decimal_places=2)
    signed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
        ]

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('status_change', 'Status Change'),
        ('document_upload', 'Document Upload'),
    )
    
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']