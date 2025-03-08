from django.db import models
from accounts.models import CustomUser
from django.utils.text import slugify
from tenders.models import Category, SubCategory, Tender
from django.core.validators import MinValueValidator, MaxValueValidator

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
    
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='bids_bids')
    bidder = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bids_submitted_bids')
    
    # Pricing
    total_price = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3, default='TSH')
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
        ('Other', 'Other Documents'),
    )
    
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='bid_documents/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class EvaluationCriterion(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='bids_evaluation_criteria')
    name = models.CharField(max_length=200)
    description = models.TextField()
    weight = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_score = models.DecimalField(max_digits=5, decimal_places=2)

class EvaluationResponse(models.Model):
    criterion = models.ForeignKey(EvaluationCriterion, on_delete=models.CASCADE)
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_evaluations')
    score = models.DecimalField(max_digits=5, decimal_places=2)
    comments = models.TextField(blank=True)
    evaluated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='bids_evaluation_responses')
    evaluated_at = models.DateTimeField(auto_now_add=True)

class Contract(models.Model):
    tender = models.OneToOneField(Tender, on_delete=models.CASCADE, related_name='bids_contract')
    bid = models.OneToOneField(Bid, on_delete=models.CASCADE, related_name='bids_awarded_contract')
    start_date = models.DateField()
    end_date = models.DateField()
    value = models.DecimalField(max_digits=16, decimal_places=2)
    signed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='bids_signed_contracts')
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
    
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='bids_audit_logs')
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='bids_audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']