# admin.py
from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.admin import SimpleListFilter
from .models import (
    Category, SubCategory, ProcurementProcess,
    Tender, TenderDocument, TenderSubscription,
    NotificationPreference, TenderNotification
)

# Custom filters
class BudgetRangeFilter(SimpleListFilter):
    title = 'Budget Range'
    parameter_name = 'budget_range'

    def lookups(self, request, model_admin):
        return (
            ('low', 'Low (< 1M)'),
            ('medium', 'Medium (1M - 10M)'),
            ('high', 'High (> 10M)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(estimated_budget__lt=1000000)
        if self.value() == 'medium':
            return queryset.filter(estimated_budget__gte=1000000,
                                estimated_budget__lte=10000000)
        if self.value() == 'high':
            return queryset.filter(estimated_budget__gt=10000000)

# Basic admin classes for supporting models
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug']
    list_filter = ['category']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(ProcurementProcess)
class ProcurementProcessAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'description']
    list_filter = ['type']
    search_fields = ['name', 'description']

# Inline for Tender Documents
class TenderDocumentInline(admin.TabularInline):
    model = TenderDocument
    extra = 1
    fields = ['file', 'uploaded_at']
    readonly_fields = ['uploaded_at']

# Inline for Tender Notifications
class TenderNotificationInline(admin.TabularInline):
    model = TenderNotification
    extra = 0
    fields = ['subscription', 'is_sent', 'sent_at', 'delivery_status', 'created_at']
    readonly_fields = ['is_sent', 'sent_at', 'delivery_status', 'created_at']
    can_delete = False

# Main Tender Admin
@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'title', 'status',
                   'category', 'SubCategory', 'publication_date',
                   'submission_deadline', 'get_document_count',
                   'get_notification_count']
    list_filter = ['status', 'category', 'SubCategory', 'procurement_process',
                  BudgetRangeFilter]
    search_fields = ['title', 'reference_number', 'description']
    date_hierarchy = 'publication_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'reference_number', 'description',
                      'category', 'SubCategory', 'procurement_process')
        }),
        ('Timeline', {
            'fields': ('publication_date', 'submission_deadline',
                      'clarification_deadline', 'evaluation_start_date',
                      'evaluation_end_date')
        }),
        ('Financial', {
            'fields': ('estimated_budget', 'currency', 'bid_bond_percentage')
        }),
        ('Location', {
            'fields': ('address',)
        }),
        ('Status', {
            'fields': ('status', 'created_by', 'last_status_change',
                      'version')
        }),
    )
    
    inlines = [
        TenderDocumentInline,
        TenderNotificationInline
    ]
    
    readonly_fields = ['last_status_change', 'created_at', 'updated_at']
    actions = ['mark_as_published', 'mark_as_canceled']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'SubCategory', 'procurement_process', 'created_by'
        ).prefetch_related(
            'documents', 'notifications'
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['submission_deadline'].widget = forms.DateTimeInput(
            attrs={'type': 'datetime-local'}
        )
        form.base_fields['clarification_deadline'].widget = forms.DateTimeInput(
            attrs={'type': 'datetime-local'}
        )
        return form

    def clean(self, form, obj):
        if obj.submission_deadline <= obj.publication_date:
            raise ValidationError("Submission deadline must be after publication date")
        if obj.clarification_deadline > obj.submission_deadline:
            raise ValidationError("Clarification deadline must be before submission deadline")
        super().clean(form, obj)

    def mark_as_published(self, request, queryset):
        queryset.update(status='published')
        self.message_user(request, "Selected tenders have been marked as published")
    mark_as_published.short_description = "Mark selected tenders as published"

    def mark_as_canceled(self, request, queryset):
        queryset.update(status='canceled')
        self.message_user(request, "Selected tenders have been marked as canceled")
    mark_as_canceled.short_description = "Mark selected tenders as canceled"

    def get_document_count(self, obj):
        return obj.documents.count()
    get_document_count.short_description = "Documents"

    def get_notification_count(self, obj):
        return obj.notifications.count()
    get_notification_count.short_description = "Notifications"

    def has_change_permission(self, request, obj=None):
        if obj and obj.status in ['awarded', 'closed', 'canceled']:
            if not request.user.is_superuser:
                return False
        return super().has_change_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status in ['awarded', 'closed', 'canceled']:
            return self.readonly_fields + ['status']
        return self.readonly_fields

# Notification-related admin classes
@admin.register(TenderSubscription)
class TenderSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'subcategory', 'procurement_process',
                   'is_active', 'created_at', 'get_keywords']
    list_filter = ['is_active', 'category', 'subcategory', 'procurement_process']
    search_fields = ['user__username', 'keywords']
    readonly_fields = ['created_at', 'updated_at']

    def get_keywords(self, obj):
        return obj.keywords if obj.keywords else "No keywords"
    get_keywords.short_description = "Keywords"

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_notifications', 'notification_frequency',
                   'last_notified', 'created_at']
    list_filter = ['email_notifications', 'notification_frequency']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at', 'last_notified']

@admin.register(TenderNotification)
class TenderNotificationAdmin(admin.ModelAdmin):
    list_display = ['tender', 'subscription', 'is_sent', 'sent_at',
                   'delivery_status', 'created_at']
    list_filter = ['is_sent', 'delivery_status']
    search_fields = ['tender__title', 'subscription__user__username']
    readonly_fields = ['sent_at', 'delivery_status', 'created_at']
    list_select_related = ['tender', 'subscription__user']