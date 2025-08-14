from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from accounts.models import (
    CustomUser, Company, CompanyFinancialStatement, CompanyAnnualTurnover,
    CompanyPersonnel, CompanySourceOfFund, CompanyExperience, CompanyOffice,
    CompanyDocument, CompanyCertification, CompanyLitigation
)
from tenders.models import (
    Tender, TenderRequiredDocument, TenderFinancialRequirement,
    TenderTurnoverRequirement, TenderExperienceRequirement,
    TenderPersonnelRequirement, TenderScheduleItem, TenderTechnicalSpecification
)

class Bid(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_evaluation', 'Under Evaluation'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='bids_bids')
    bidder = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='bids_submitted')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bids_bids')
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    total_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    currency = models.CharField(max_length=3, choices=Tender.CurrencyTYpes, default='TZS')
    submission_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    validity_complied = models.BooleanField(default=False)
    completion_complied = models.BooleanField(default=False)
    proposed_completion_days = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    jv_partner = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='bids_jv_partner')
    jv_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))])
    created_at = models.DateTimeField(null=True, blank=True)  # Temporary change
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('tender', 'company')]
        indexes = [models.Index(fields=['slug', 'status'])]
        ordering = ['-created_at']

    def __str__(self):
        return f"Bid {self.slug} for {self.tender.reference_number}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.tender.reference_number}-{self.company.name}")
            self.slug = base_slug
            counter = 1
            while Bid.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        if self.status == 'submitted' and not self.submission_date:
            self.submission_date = timezone.now()
        if not self.created_at:  # Set created_at for new records
            self.created_at = timezone.now()
        super().save(*args, **kwargs)

    def clean(self):
        if self.jv_partner and (self.jv_percentage is None or self.jv_percentage <= 0 or self.jv_percentage >= 100):
            raise ValidationError("JV percentage must be between 0 and 100 when a JV partner is specified.")
        if self.tender.completion_period_days:
            if not self.completion_complied and not self.proposed_completion_days:
                raise ValidationError("Must either comply with completion period or propose an alternative.")
            if self.proposed_completion_days and not self.tender.allow_alternative_delivery:
                raise ValidationError("Alternative completion period not allowed for this tender.")
        super().clean()

# ... (other models remain unchanged, as provided)
class BidDocument(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_documents')
    tender_document = models.ForeignKey(TenderRequiredDocument, on_delete=models.CASCADE, related_name='bids_documents')
    company_document = models.ForeignKey(CompanyDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name='bids_documents')
    company_certification = models.ForeignKey(CompanyCertification, on_delete=models.SET_NULL, null=True, blank=True, related_name='bids_documents')
    file = models.FileField(upload_to='bid_docs/%Y/%m/', null=True, blank=True)
    description = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('bid', 'tender_document')]
        ordering = ['submitted_at']

    def __str__(self):
        return f"Document {self.tender_document.name} for Bid {self.bid.slug}"

    def clean(self):
        if not (self.file or self.company_document or self.company_certification):
            raise ValidationError("At least one of file, company_document, or company_certification must be provided.")

class BidFinancialResponse(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_financial_responses')
    financial_requirement = models.ForeignKey(TenderFinancialRequirement, on_delete=models.CASCADE, related_name='bids_financial_responses')
    financial_statement = models.ForeignKey(CompanyFinancialStatement, on_delete=models.SET_NULL, null=True, related_name='bids_financial_responses')
    actual_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    complied = models.BooleanField(default=False)
    jv_contribution = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))])
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('bid', 'financial_requirement')]
        ordering = ['financial_requirement__name']

    def __str__(self):
        return f"Financial Response for {self.financial_requirement.name} in Bid {self.bid.slug}"

    def evaluate(self):
        if self.financial_statement and self.financial_requirement.minimum is not None:
            field_map = {
                'Current Ratio': 'current_ratio',
                'Cash Ratio': 'cash_ratio',
                'Working Capital': 'working_capital',
                'Gross Profit Margin': 'gross_profit_margin',
                'Debt to Equity Ratio': 'debt_to_equity_ratio',
                'Return on Assets': 'return_on_assets',
            }
            field = field_map.get(self.financial_requirement.name, 'total_assets')
            actual_value = getattr(self.financial_statement, field, 0)
            self.actual_value = Decimal(str(actual_value))
            self.complied = self.actual_value >= self.financial_requirement.minimum
            self.save()
        return self.complied

class BidTurnoverResponse(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_turnover_responses')
    turnover_requirement = models.ForeignKey(TenderTurnoverRequirement, on_delete=models.CASCADE, related_name='bids_turnover_responses')
    turnovers = models.ManyToManyField(CompanyAnnualTurnover, related_name='bids_turnover_responses')
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    currency = models.CharField(max_length=3, choices=Tender.CurrencyTYpes, default='TZS')
    complied = models.BooleanField(default=False)
    jv_contribution = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))])
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('bid', 'turnover_requirement')]
        ordering = ['turnover_requirement__label']

    def __str__(self):
        return f"Turnover Response for {self.turnover_requirement.label} in Bid {self.bid.slug}"

    def evaluate(self):
        if self.turnovers.exists() and self.turnover_requirement.amount is not None:
            self.actual_amount = sum(t.amount for t in self.turnovers.all()) / self.turnovers.count()
            self.currency = self.turnovers.first().currency
            self.complied = self.actual_amount >= self.turnover_requirement.amount
            self.save()
        return self.complied

class BidExperienceResponse(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_experience_responses')
    experience_requirement = models.ForeignKey(TenderExperienceRequirement, on_delete=models.CASCADE, related_name='bids_experience_responses')
    company_experience = models.ForeignKey(CompanyExperience, on_delete=models.SET_NULL, null=True, related_name='bids_experience_responses')
    complied = models.BooleanField(default=False)
    jv_contribution = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))])
    notes = models.TextField(blank=True)
    proof = models.FileField(upload_to='bid_experience/%Y/%m/', null=True, blank=True)

    class Meta:
        unique_together = [('bid', 'experience_requirement')]
        ordering = ['experience_requirement__type']

    def __str__(self):
        return f"Experience Response for {self.experience_requirement.type} in Bid {self.bid.slug}"

    def evaluate(self):
        if self.company_experience and self.experience_requirement.contract_count is not None and self.experience_requirement.min_value is not None:
            self.complied = (self.company_experience.contract_count >= self.experience_requirement.contract_count and
                            self.company_experience.total_value >= self.experience_requirement.min_value)
            self.save()
        return self.complied

class BidPersonnelResponse(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_personnel_responses')
    personnel_requirement = models.ForeignKey(TenderPersonnelRequirement, on_delete=models.CASCADE, related_name='bids_personnel_responses')
    personnel = models.ForeignKey(CompanyPersonnel, on_delete=models.SET_NULL, null=True, related_name='bids_personnel_responses')
    complied = models.BooleanField(default=False)
    jv_contribution = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))])
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('bid', 'personnel_requirement')]
        ordering = ['personnel_requirement__role']

    def __str__(self):
        return f"Personnel Response for {self.personnel_requirement.role} in Bid {self.bid.slug}"

    def evaluate(self):
        if self.personnel and self.personnel_requirement.min_experience_yrs is not None:
            self.complied = self.personnel.years_of_experience >= self.personnel_requirement.min_experience_yrs
            if self.personnel_requirement.min_education and self.personnel.education_level:
                self.complied = self.complied and self.personnel.education_level.lower() == self.personnel_requirement.min_education.lower()
            if self.personnel_requirement.age_min and self.personnel.age:
                self.complied = self.complied and self.personnel.age >= self.personnel_requirement.age_min
            if self.personnel_requirement.age_max and self.personnel.age:
                self.complied = self.complied and self.personnel.age <= self.personnel_requirement.age_max
            if self.personnel_requirement.professional_registration and self.personnel.professional_certifications:
                self.complied = self.complied and self.personnel_requirement.professional_registration.lower() in self.personnel.professional_certifications.lower()
            self.save()
        return self.complied

class BidOfficeResponse(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_office_responses')
    office = models.ForeignKey(CompanyOffice, on_delete=models.SET_NULL, null=True, related_name='bids_office_responses')
    tender_document = models.ForeignKey(TenderRequiredDocument, on_delete=models.CASCADE, related_name='bids_office_responses')
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('bid', 'tender_document')]
        ordering = ['tender_document__name']

    def __str__(self):
        return f"Office Response for {self.tender_document.name} in Bid {self.bid.slug}"

class BidSourceResponse(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_source_responses')
    tender_document = models.ForeignKey(TenderRequiredDocument, on_delete=models.CASCADE, related_name='bids_source_responses')
    sources = models.ManyToManyField(CompanySourceOfFund, related_name='bids_source_responses')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    currency = models.CharField(max_length=3, choices=Tender.CurrencyTYpes, default='TZS')
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('bid', 'tender_document')]
        ordering = ['tender_document__name']

    def __str__(self):
        return f"Source Response for {self.tender_document.name} in Bid {self.bid.slug}"

    def calculate_total_amount(self):
        if self.sources.exists():
            self.total_amount = sum(source.amount for source in self.sources.all())
            self.currency = self.sources.first().currency
            self.save()
        return self.total_amount

class BidLitigationResponse(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_litigation_responses')
    tender_document = models.ForeignKey(TenderRequiredDocument, on_delete=models.CASCADE, related_name='bids_litigation_responses')
    litigations = models.ManyToManyField(CompanyLitigation, related_name='bids_litigation_responses')
    no_litigation = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('bid', 'tender_document')]
        ordering = ['tender_document__name']

    def __str__(self):
        return f"Litigation Response for {self.tender_document.name} in Bid {self.bid.slug}"

    def clean(self):
        if self.no_litigation and self.litigations.exists():
            raise ValidationError("Cannot select litigations if 'no litigation' is checked.")

class BidScheduleResponse(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_schedule_responses')
    schedule_item = models.ForeignKey(TenderScheduleItem, on_delete=models.CASCADE, related_name='bids_schedule_responses')
    proposed_quantity = models.PositiveIntegerField()
    proposed_delivery_date = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('bid', 'schedule_item')]
        ordering = ['schedule_item__commodity']

    def __str__(self):
        return f"Schedule Response for {self.schedule_item.commodity} in Bid {self.bid.slug}"

class BidTechnicalResponse(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_technical_responses')
    technical_specification = models.ForeignKey(TenderTechnicalSpecification, on_delete=models.CASCADE, related_name='bids_technical_responses')
    description = models.TextField(blank=True)
    complied = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('bid', 'technical_specification')]
        ordering = ['technical_specification__category']

    def __str__(self):
        return f"Technical Response for {self.technical_specification.category} in Bid {self.bid.slug}"

class BidEvaluation(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_evaluations')
    evaluator = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='bids_evaluated')
    score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))])
    comments = models.TextField(blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-evaluated_at']

    def __str__(self):
        return f"Evaluation for Bid {self.bid.slug} by {self.evaluator.email}"

class BidAuditLog(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='bids_audit_logs')
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='bids_audit_logs')
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Audit Log: {self.action} for Bid {self.bid.slug}"