from django.contrib import admin
from .models import (
    Category, SubCategory, ProductService, ProductImage,
    PriceList, QuoteRequest, CompanyReview, Message, Notification
)
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'subcategory_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']
    actions = ['make_active', 'make_inactive']

    def subcategory_count(self, obj):
        return obj.subcategories.count()
    subcategory_count.short_description = 'Subcategories'

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "Selected categories have been activated", messages.SUCCESS)
    make_active.short_description = "Mark selected categories as active"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "Selected categories have been deactivated", messages.WARNING)
    make_inactive.short_description = "Mark selected categories as inactive"

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'slug', 'description', 'category__name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']
    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "Selected subcategories have been activated", messages.SUCCESS)
    make_active.short_description = "Mark selected subcategories as active"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "Selected subcategories have been deactivated", messages.WARNING)
    make_inactive.short_description = "Mark selected subcategories as inactive"

@admin.register(ProductService)
class ProductServiceAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'company', 'category', 'subcategory', 
        'type', 'is_active', 'created_at', 'updated_at'
    ]
    list_filter = ['type', 'category', 'subcategory', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'company__name', 'category__name']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']
    fieldsets = (
        (None, {
            'fields': ('company', 'name', 'description')
        }),
        ('Categorization', {
            'fields': ('category', 'subcategory', 'type')
        }),
        ('Images', {
            'fields': ('featured_image',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "Selected products/services have been activated", messages.SUCCESS)
    make_active.short_description = "Mark selected products/services as active"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "Selected products/services have been deactivated", messages.WARNING)
    make_inactive.short_description = "Mark selected products/services as inactive"

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product_service', 'image_preview', 'caption', 'is_primary', 'created_at']
    list_filter = ['is_primary', 'created_at', 'product_service__company']
    search_fields = ['caption', 'product_service__name']
    readonly_fields = ['created_at', 'image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px;"/>',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = 'Image Preview'

@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = [
        'product_service', 'unit_price', 'unit', 
        'minimum_quantity', 'is_active', 'created_at', 'updated_at'
    ]
    list_filter = ['is_active', 'created_at', 'product_service__company']
    search_fields = ['product_service__name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']
    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "Selected prices have been activated", messages.SUCCESS)
    make_active.short_description = "Mark selected prices as active"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "Selected prices have been deactivated", messages.WARNING)
    make_inactive.short_description = "Mark selected prices as inactive"

@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'product_service', 'quantity', 'status',
        'total_price', 'created_at', 'updated_at'
    ]
    list_filter = ['status', 'created_at', 'product_service__company']
    search_fields = [
        'customer__email', 'product_service__name', 
        'additional_details'
    ]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('customer', 'product_service', 'quantity')
        }),
        ('Details', {
            'fields': ('additional_details', 'status', 'total_price')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    actions = ['mark_accepted', 'mark_rejected', 'mark_cancelled']

    def mark_accepted(self, request, queryset):
        queryset.update(status='ACCEPTED')
        self.message_user(request, "Selected quotes have been marked as accepted", messages.SUCCESS)
    mark_accepted.short_description = "Mark selected quotes as accepted"

    def mark_rejected(self, request, queryset):
        queryset.update(status='REJECTED')
        self.message_user(request, "Selected quotes have been marked as rejected", messages.WARNING)
    mark_rejected.short_description = "Mark selected quotes as rejected"

    def mark_cancelled(self, request, queryset):
        queryset.update(status='CANCELLED')
        self.message_user(request, "Selected quotes have been marked as cancelled", messages.WARNING)
    mark_cancelled.short_description = "Mark selected quotes as cancelled"

@admin.register(CompanyReview)
class CompanyReviewAdmin(admin.ModelAdmin):
    list_display = [
        'company', 'user', 'rating', 'is_approved', 
        'created_at', 'updated_at'
    ]
    list_filter = ['rating', 'is_approved', 'created_at', 'company']
    search_fields = ['comment', 'company__name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_approved']
    actions = ['approve_reviews', 'reject_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, "Selected reviews have been approved", messages.SUCCESS)
    approve_reviews.short_description = "Approve selected reviews"

    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, "Selected reviews have been rejected", messages.WARNING)
    reject_reviews.short_description = "Reject selected reviews"

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'sender', 'receiver', 'short_content', 
        'is_read', 'created_at', 'has_parent'
    ]
    list_filter = ['is_read', 'created_at', 'sender', 'receiver']
    search_fields = ['content', 'sender__email', 'receiver__email']
    readonly_fields = ['created_at']
    
    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = 'Content Preview'

    def has_parent(self, obj):
        return bool(obj.parent)
    has_parent.boolean = True
    has_parent.short_description = 'Has Parent'

    actions = ['mark_read', 'mark_unread']

    def mark_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, "Selected messages have been marked as read", messages.SUCCESS)
    mark_read.short_description = "Mark selected messages as read"

    def mark_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, "Selected messages have been marked as unread", messages.WARNING)
    mark_unread.short_description = "Mark selected messages as unread"

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'notification_type', 'short_message',
        'is_read', 'created_at', 'related_quote_link'
    ]
    list_filter = ['notification_type', 'is_read', 'created_at', 'user']
    search_fields = ['message', 'user__email']
    readonly_fields = ['created_at']
    
    def short_message(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    short_message.short_description = 'Message Preview'

    def related_quote_link(self, obj):
        if obj.related_quote:
            url = reverse('admin:marketplace_quoterequest_change', 
                         args=[obj.related_quote.id])
            return format_html('<a href="{}">Quote #{}</a>', 
                             url, obj.related_quote.id)
        return "-"
    related_quote_link.short_description = 'Related Quote'

    actions = ['mark_read', 'mark_unread']

    def mark_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, "Selected notifications have been marked as read", messages.SUCCESS)
    mark_read.short_description = "Mark selected notifications as read"

    def mark_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, "Selected notifications have been marked as unread", messages.WARNING)
    mark_unread.short_description = "Mark selected notifications as unread"