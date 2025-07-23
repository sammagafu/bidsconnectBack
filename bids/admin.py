from django.contrib import admin

from .models import Bid, BidDocument, AuditLog


class BidDocumentInline(admin.TabularInline):
    model = BidDocument
    extra = 0
    fields = ['required_document', 'file', 'uploaded_at']
    readonly_fields = ['uploaded_at']


# Admin actions for status transitions
@admin.action(description='Mark selected bids as Submitted')
def make_submitted(modeladmin, request, queryset):
    queryset.update(status='submitted')

@admin.action(description='Mark selected bids as Under Review')
def make_under_review(modeladmin, request, queryset):
    queryset.update(status='under_review')

@admin.action(description='Mark selected bids as Technically Qualified')
def make_qualified(modeladmin, request, queryset):
    queryset.update(status='qualified')

@admin.action(description='Mark selected bids as Disqualified')
def make_disqualified(modeladmin, request, queryset):
    queryset.update(status='disqualified')

@admin.action(description='Mark selected bids as Awarded')
def make_awarded(modeladmin, request, queryset):
    queryset.update(status='awarded')

@admin.action(description='Mark selected bids as Withdrawn')
def make_withdrawn(modeladmin, request, queryset):
    queryset.update(status='withdrawn')


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ['id', 'tender_title', 'bidder_email', 'company_name', 'validity_days', 'status', 'submission_date']
    list_filter = ['status', 'tender', 'submission_date']
    search_fields = ['tender__title', 'bidder__email', 'company__name']
    list_select_related = ['tender', 'bidder', 'company']
    inlines = [BidDocumentInline]
    actions = [
        make_submitted,
        make_under_review,
        make_qualified,
        make_disqualified,
        make_awarded,
        make_withdrawn,
    ]
    readonly_fields = ['submission_date']

    def tender_title(self, obj):
        return obj.tender.title
    tender_title.short_description = 'Tender'

    def bidder_email(self, obj):
        return obj.bidder.email
    bidder_email.short_description = 'Bidder Email'

    def company_name(self, obj):
        return obj.company.name
    company_name.short_description = 'Company'


@admin.register(BidDocument)
class BidDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'bid_id', 'required_document', 'file', 'uploaded_at']
    list_filter = ['required_document', 'uploaded_at']
    search_fields = ['bid__tender__title', 'bid__bidder__email']
    readonly_fields = ['uploaded_at']

    def bid_id(self, obj):
        return obj.bid.id
    bid_id.short_description = 'Bid ID'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'tender_title', 'user_email', 'action', 'timestamp']
    list_filter = ['action', 'tender', 'timestamp']
    search_fields = ['tender__title', 'user__email', 'details']
    readonly_fields = ['timestamp']
    list_select_related = ['tender', 'user']

    def tender_title(self, obj):
        return obj.tender.title
    tender_title.short_description = 'Tender'

    def user_email(self, obj):
        return obj.user.email if obj.user else 'N/A'
    user_email.short_description = 'User'
