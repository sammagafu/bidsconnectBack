from django.contrib import admin
from django.core.exceptions import ValidationError
from .models import (
    Category, SubCategory, ProcurementProcess, Tender, TenderDocument,
    TenderSubscription, NotificationPreference, TenderNotification, TenderStatusHistory
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    list_filter = ('name',)
    search_fields = ('name', 'slug')

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'category_name')
    list_filter = ('category',)
    search_fields = ('name', 'slug', 'description')

    def category_name(self, obj):
        return obj.category.name
    category_name.short_description = 'Category'

@admin.register(ProcurementProcess)
class ProcurementProcessAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'type')
    list_filter = ('type', 'name')
    search_fields = ('name', 'slug', 'description')

@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'reference_number', 'status', 'category_name', 'subcategory_name', 'procurement_process_name')
    list_filter = ('status', 'category', 'subcategory', 'procurement_process', 'tender_type_country', 'tender_type_sector')
    search_fields = ('title', 'reference_number', 'tenderdescription')
    readonly_fields = ('created_by', 'created_at', 'updated_at', 'last_status_change')

    def clean(self):
        """Validate that when tender_securing_type is 'Tender Security', either percentage or amount is provided."""
        data = self.cleaned_data
        if data.get('tender_securing_type') == 'Tender Security':
            if not (data.get('tender_Security_percentage') or data.get('tender_Security_amount')):
                raise ValidationError(
                    "When Tender Securing Type is 'Tender Security', you must provide either Security Percentage or Security Amount."
                )
        return data

    def save_model(self, request, obj, form, change):
        """Ensure form validation is called before saving."""
        form.full_clean()  # Trigger clean method
        super().save_model(request, obj, form, change)

    def category_name(self, obj):
        return obj.category.name if obj.category else '-'
    category_name.short_description = 'Category'

    def subcategory_name(self, obj):
        return obj.subcategory.name if obj.subcategory else '-'
    subcategory_name.short_description = 'Subcategory'

    def procurement_process_name(self, obj):
        return obj.procurement_process.name if obj.procurement_process else '-'
    procurement_process_name.short_description = 'Procurement Process'

@admin.register(TenderDocument)
class TenderDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'tender_title', 'file', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('tender__title',)

    def tender_title(self, obj):
        return obj.tender.title
    tender_title.short_description = 'Tender'

@admin.register(TenderSubscription)
class TenderSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_username', 'category_name', 'subcategory_name', 'procurement_process_name', 'is_active')
    list_filter = ('is_active', 'category', 'subcategory', 'procurement_process')
    search_fields = ('user__username', 'category__name', 'subcategory__name', 'procurement_process__name', 'keywords')
    readonly_fields = ('user', 'created_at', 'updated_at')

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'User'

    def category_name(self, obj):
        return obj.category.name if obj.category else '-'
    category_name.short_description = 'Category'

    def subcategory_name(self, obj):
        return obj.subcategory.name if obj.subcategory else '-'
    subcategory_name.short_description = 'Subcategory'

    def procurement_process_name(self, obj):
        return obj.procurement_process.name if obj.procurement_process else '-'
    procurement_process_name.short_description = 'Procurement Process'

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_username', 'email_notifications', 'notification_frequency')
    list_filter = ('email_notifications', 'notification_frequency')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'created_at', 'updated_at', 'last_notified')

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'User'

@admin.register(TenderNotification)
class TenderNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscription_user', 'tender_title', 'is_sent', 'sent_at', 'delivery_status')
    list_filter = ('is_sent', 'sent_at')
    search_fields = ('subscription__user__username', 'tender__title', 'delivery_status')
    readonly_fields = ('subscription', 'tender', 'sent_at', 'created_at')

    def subscription_user(self, obj):
        return obj.subscription.user.username
    subscription_user.short_description = 'User'

    def tender_title(self, obj):
        return obj.tender.title
    tender_title.short_description = 'Tender'

@admin.register(TenderStatusHistory)
class TenderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'tender_title', 'status', 'changed_at', 'changed_by_username')
    list_filter = ('status', 'changed_at')
    search_fields = ('tender__title', 'status')
    readonly_fields = ('tender', 'changed_at', 'changed_by')

    def tender_title(self, obj):
        return obj.tender.title
    tender_title.short_description = 'Tender'

    def changed_by_username(self, obj):
        return obj.changed_by.username if obj.changed_by else '-'
    changed_by_username.short_description = 'Changed By'

class TenderNotificationInline(admin.TabularInline):
    model = TenderNotification
    extra = 0
    readonly_fields = ('subscription', 'tender', 'sent_at', 'is_sent', 'delivery_status', 'created_at')
    can_delete = False