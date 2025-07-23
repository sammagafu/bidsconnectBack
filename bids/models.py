import uuid
from django.db import models
from django.core.exceptions import ValidationError

from accounts.models import CustomUser, Company
from tenders.models import Tender, TenderRequiredDocument


class Bid(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('qualified', 'Technically Qualified'),
        ('disqualified', 'Disqualified'),
        ('awarded', 'Awarded'),
        ('withdrawn', 'Withdrawn'),
    )

    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name='bids'
    )
    bidder = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='submitted_bids'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='company_bids'
    )
    validity_days = models.PositiveIntegerField(default=90)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    submission_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('tender', 'bidder')
        ordering = ['-submission_date']

    def __str__(self):
        return f"Bid {self.id} by {self.bidder} ({self.company}) on {self.tender}"


class BidDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bid = models.ForeignKey(
        Bid,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    required_document = models.ForeignKey(
        TenderRequiredDocument,
        on_delete=models.CASCADE,
        related_name='bid_documents'
    )
    file = models.FileField(upload_to='bid_documents/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('bid', 'required_document')

    def clean(self):
        # Ensure the uploaded document actually belongs to this tender
        if self.required_document.tender_id != self.bid.tender_id:
            raise ValidationError({
                'required_document': 'This document type is not required for the selected tender.'
            })

    def __str__(self):
        return f"{self.required_document.name} for Bid {self.bid.id}"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('status_change', 'Status Change'),
        ('document_upload', 'Document Upload'),
    )

    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_action_display()} by {self.user} on {self.timestamp}"
