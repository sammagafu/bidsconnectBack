# models.py
from django.db import models
from django.utils.text import slugify
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

class PowerOfAttorney(models.Model):
    """
    Model representing a Power of Attorney document with all necessary details.
    """
    # Document metadata
    document_date = models.DateField(
        help_text="Date when the power of attorney document is issued"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        help_text="Unique identifier derived from tender number"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated"
    )

    # Company details
    company_name = models.CharField(
        max_length=100,
        help_text="Name of the company granting power of attorney"
    )
    company_address = models.TextField(
        help_text="Complete address of the company"
    )
    company_po_box = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^P\.O\. Box \d+.*$',
                message="PO Box must start with 'P.O. Box' followed by number"
            )
        ],
        help_text="Company's PO Box (format: P.O. Box XXX...)"
    )

    # Attorney details
    attorney_name = models.CharField(
        max_length=100,
        help_text="Full name of the appointed attorney"
    )
    attorney_po_box = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^P\.O\. Box \d+.*$',
                message="PO Box must start with 'P.O. Box' followed by number"
            )
        ],
        help_text="Attorney's PO Box (format: P.O. Box XXX...)"
    )
    attorney_address = models.TextField(
        blank=True,
        help_text="Complete address of the attorney (optional)"
    )

    # Tender details
    tender_number = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9/]+$',
                message="Tender number must contain only letters, numbers, and slashes"
            )
        ],
        help_text="Unique tender reference number (e.g., FA/2024/2025/217/TR149/G/13)"
    )
    tender_description = models.CharField(
        max_length=200,
        help_text="Brief description of the tender purpose"
    )
    tender_beneficiary = models.CharField(
        max_length=100,
        help_text="Organization benefiting from the tender"
    )

    # Witness/Commissioner details
    witness_name = models.CharField(
        max_length=100,
        help_text="Full name of the witness/commissioner for oaths"
    )
    witness_po_box = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^P\.O\. Box \d+.*$',
                message="PO Box must start with 'P.O. Box' followed by number"
            )
        ],
        help_text="Witness's PO Box (format: P.O. Box XXX...)"
    )
    witness_title = models.CharField(
        max_length=100,
        help_text="Professional title of the witness (e.g., Advocate, Notary Public)"
    )
    witness_address = models.TextField(
        blank=True,
        help_text="Complete address of the witness (optional)"
    )

    class Meta:
        verbose_name = "Power of Attorney"
        verbose_name_plural = "Powers of Attorney"
        ordering = ['-document_date', 'tender_number']

    def __str__(self):
        """
        String representation of the Power of Attorney instance.
        """
        return f"POA - {self.company_name} to {self.attorney_name} ({self.tender_number})"

    def save(self, *args, **kwargs):
        """
        Override save method to:
        1. Convert tender_number to uppercase
        2. Generate slug from tender_number
        """
        # Convert tender_number to uppercase
        self.tender_number = self.tender_number.upper()

        # Generate slug from tender_number
        if not self.slug or self.tender_number != self.slug.replace('-', '/'):
            # Replace slashes with hyphens for URL-friendly slug
            base_slug = slugify(self.tender_number.replace('/', '-'))
            # Ensure uniqueness
            slug = base_slug
            counter = 1
            while PowerOfAttorney.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)

    def clean(self):
        """
        Add custom validation for the model.
        """
        super().clean()
        if not self.document_date:
            raise ValidationError("Document date is required")