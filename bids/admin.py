from django.contrib import admin
from .models import (
    Bid, BidDocument, BidFinancialResponse, BidTurnoverResponse,
    BidExperienceResponse, BidPersonnelResponse, BidOfficeResponse,
    BidSourceResponse, BidLitigationResponse, BidScheduleResponse,
    BidTechnicalResponse, BidEvaluation, BidAuditLog
)

class BidDocumentInline(admin.TabularInline):
    model = BidDocument
    extra = 0
    fields = ['tender_document', 'company_document', 'company_certification', 'file', 'description', 'submitted_at']
    readonly_fields = ['submitted_at']

# Admin actions for status transitions, aligned with Bid.STATUS_CHOICES
@admin.action(description='Mark selected bids as Submitted')
def make_submitted(modeladmin, request, queryset):
    queryset.update(status='submitted')

@admin.action(description='Mark selected bids as Under Evaluation')
def make_under_evaluation(modeladmin, request, queryset):
    queryset.update(status='under_evaluation')

@admin.action(description='Mark selected bids as Accepted')
def make_accepted(modeladmin, request, queryset):
    queryset.update(status='accepted')

@admin.action(description='Mark selected bids as Rejected')
def make_rejected(modeladmin, request, queryset):
    queryset.update(status='rejected')

@admin.action(description='Mark selected bids as Withdrawn')
def make_withdrawn(modeladmin, request, queryset):
    queryset.update(status='withdrawn')

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ['id', 'tender_reference', 'bidder_email', 'company_name', 'status', 'total_price', 'currency', 'submission_date', 'created_at']
    list_filter = ['status', 'tender', 'submission_date', 'created_at']
    search_fields = ['tender__reference_number', 'bidder__email', 'company__name', 'slug']
    list_select_related = ['tender', 'bidder', 'company']
    inlines = [BidDocumentInline]
    actions = [
        make_submitted,
        make_under_evaluation,
        make_accepted,
        make_rejected,
        make_withdrawn,
    ]
    readonly_fields = ['slug', 'submission_date', 'created_at', 'updated_at']

    def tender_reference(self, obj):
        return obj.tender.reference_number
    tender_reference.short_description = 'Tender'

    def bidder_email(self, obj):
        return obj.bidder.email if obj.bidder else 'N/A'
    bidder_email.short_description = 'Bidder Email'

    def company_name(self, obj):
        return obj.company.name
    company_name.short_description = 'Company'

@admin.register(BidDocument)
class BidDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'tender_document', 'company_document', 'company_certification', 'file', 'submitted_at']
    list_filter = ['tender_document', 'submitted_at']
    search_fields = ['bid__slug', 'tender_document__name']
    readonly_fields = ['submitted_at']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

@admin.register(BidFinancialResponse)
class BidFinancialResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'financial_requirement', 'actual_value', 'complied', 'jv_contribution']
    list_filter = ['complied']
    search_fields = ['bid__slug', 'financial_requirement__name']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

@admin.register(BidTurnoverResponse)
class BidTurnoverResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'turnover_requirement', 'actual_amount', 'currency', 'complied', 'jv_contribution']
    list_filter = ['complied', 'currency']
    search_fields = ['bid__slug', 'turnover_requirement__label']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

@admin.register(BidExperienceResponse)
class BidExperienceResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'experience_requirement', 'company_experience', 'complied', 'jv_contribution']
    list_filter = ['complied']
    search_fields = ['bid__slug', 'experience_requirement__type']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

@admin.register(BidPersonnelResponse)
class BidPersonnelResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'personnel_requirement', 'get_personnels', 'complied', 'jv_contribution']
    list_filter = ['complied']
    search_fields = ['bid__slug', 'personnel_requirement__role']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

    def get_personnels(self, obj):
        return ", ".join([str(personnel) for personnel in obj.personnels.all()])
    get_personnels.short_description = 'Personnels'

@admin.register(BidOfficeResponse)
class BidOfficeResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'tender_document', 'company_office']
    search_fields = ['bid__slug', 'tender_document__name']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

@admin.register(BidSourceResponse)
class BidSourceResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'tender_document', 'total_amount', 'currency']
    search_fields = ['bid__slug', 'tender_document__name']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

@admin.register(BidLitigationResponse)
class BidLitigationResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'tender_document', 'no_litigation']
    list_filter = ['no_litigation']
    search_fields = ['bid__slug', 'tender_document__name']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

@admin.register(BidScheduleResponse)
class BidScheduleResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'schedule_item', 'proposed_quantity', 'proposed_delivery_date']
    search_fields = ['bid__slug', 'schedule_item__commodity']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

@admin.register(BidTechnicalResponse)
class BidTechnicalResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'technical_specification', 'complied']
    list_filter = ['complied']
    search_fields = ['bid__slug', 'technical_specification__category']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

@admin.register(BidEvaluation)
class BidEvaluationAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'evaluator_email', 'score', 'evaluated_at']
    list_filter = ['evaluated_at']
    search_fields = ['bid__slug', 'evaluator__email']
    readonly_fields = ['evaluated_at']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

    def evaluator_email(self, obj):
        return obj.evaluator.email if obj.evaluator else 'N/A'
    evaluator_email.short_description = 'Evaluator'

@admin.register(BidAuditLog)
class BidAuditLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'user_email', 'action', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['bid__slug', 'user__email', 'action', 'details']
    readonly_fields = ['created_at']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

    def user_email(self, obj):
        return obj.user.email if obj.user else 'N/A'
    user_email.short_description = 'User'