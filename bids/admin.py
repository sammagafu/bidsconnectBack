# bids/admin.py
from django.contrib import admin
from .models import (
    Bid, BidDocument, EvaluationCriterion, EvaluationResponse,
    Contract, AuditLog
)

# Inline for Bid Documents
class BidDocumentInline(admin.TabularInline):
    model = BidDocument
    extra = 1
    fields = ['document_type', 'file', 'uploaded_at']
    readonly_fields = ['uploaded_at']

# Inline for Evaluation Responses
class EvaluationResponseInline(admin.TabularInline):
    model = EvaluationResponse
    extra = 0
    fields = ['criterion', 'score', 'comments', 'evaluated_by', 'evaluated_at']
    readonly_fields = ['evaluated_at']

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ['id', 'tender_title', 'bidder_email', 'total_price', 'status', 'submission_date']
    list_filter = ['status', 'submission_date']
    search_fields = ['tender__title', 'bidder__email', 'bidder__username']
    list_select_related = ['tender', 'bidder']
    inlines = [BidDocumentInline, EvaluationResponseInline]
    readonly_fields = ['submission_date']

    def tender_title(self, obj):
        return obj.tender.title
    tender_title.short_description = 'Tender'

    def bidder_email(self, obj):
        return obj.bidder.email
    bidder_email.short_description = 'Bidder Email'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tender', 'bidder')

@admin.register(BidDocument)
class BidDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'document_type', 'file', 'uploaded_at']
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['bid__tender__title', 'bid__bidder__email']
    readonly_fields = ['uploaded_at']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

@admin.register(EvaluationCriterion)
class EvaluationCriterionAdmin(admin.ModelAdmin):
    list_display = ['id', 'tender_title', 'name', 'weight', 'max_score']
    list_filter = ['tender']
    search_fields = ['tender__title', 'name', 'description']
    list_select_related = ['tender']

    def tender_title(self, obj):
        return obj.tender.title
    tender_title.short_description = 'Tender'

@admin.register(EvaluationResponse)
class EvaluationResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'criterion_name', 'score', 'evaluated_by_email', 'evaluated_at']
    list_filter = ['evaluated_at']
    search_fields = ['bid__tender__title', 'criterion__name', 'evaluated_by__email']
    readonly_fields = ['evaluated_at']
    list_select_related = ['bid', 'criterion', 'evaluated_by']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

    def criterion_name(self, obj):
        return obj.criterion.name
    criterion_name.short_description = 'Criterion'

    def evaluated_by_email(self, obj):
        return obj.evaluated_by.email if obj.evaluated_by else 'N/A'
    evaluated_by_email.short_description = 'Evaluated By'

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['id', 'tender_title', 'bid_id', 'value', 'start_date', 'end_date', 'signed_by_email', 'signed_at']
    list_filter = ['start_date', 'end_date', 'signed_at']
    search_fields = ['tender__title', 'bid__bidder__email']
    readonly_fields = ['signed_at']
    list_select_related = ['tender', 'bid', 'signed_by']

    def tender_title(self, obj):
        return obj.tender.title
    tender_title.short_description = 'Tender'

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'

    def signed_by_email(self, obj):
        return obj.signed_by.email if obj.signed_by else 'N/A'
    signed_by_email.short_description = 'Signed By'

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'tender_title', 'user_email', 'action', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['tender__title', 'user__email', 'details']
    readonly_fields = ['timestamp']
    list_select_related = ['tender', 'user']

    def tender_title(self, obj):
        return obj.tender.title
    tender_title.short_description = 'Tender'

    def user_email(self, obj):
        return obj.user.email if obj.user else 'N/A'
    user_email.short_description = 'User'