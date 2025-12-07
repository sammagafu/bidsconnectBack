# marketplace/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from .models import (
    Category, SubCategory, ProductService, ProductImage,
    PriceList, RFQ, RFQItem, Quote, QuoteItem,
    CompanyReview, Message, Notification
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'created_at']
    list_filter = ['category']
    search_fields = ['name', 'category__name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductService)
class ProductServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'category', 'subcategory', 'type', 'is_active', 'created_at']
    list_filter = ['type', 'category', 'subcategory', 'is_active']
    search_fields = ['name', 'company__name', 'description']
    list_editable = ['is_active']


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product_service', 'image_preview', 'is_primary']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 70px;"/>', obj.image.url)
        return "(No image)"
    image_preview.short_description = "Preview"


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ['product_service', 'unit_price', 'unit', 'minimum_quantity', 'is_active']
    list_filter = ['is_active']
    list_editable = ['is_active']


@admin.register(RFQ)
class RFQAdmin(admin.ModelAdmin):
    list_display = ['title', 'buyer', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'buyer__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RFQItem)
class RFQItemAdmin(admin.ModelAdmin):
    list_display = ['rfq', 'name', 'quantity', 'category', 'subcategory', 'created_at']
    list_filter = ['type', 'category', 'subcategory']
    search_fields = ['name', 'rfq__title']


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['rfq', 'seller', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['rfq__title', 'seller__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(QuoteItem)
class QuoteItemAdmin(admin.ModelAdmin):
    list_display = ['quote', 'rfq_item', 'proposed_price']
    search_fields = ['rfq_item__name']


@admin.register(CompanyReview)
class CompanyReviewAdmin(admin.ModelAdmin):
    list_display = ['company', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating']
    search_fields = ['company__name', 'user__email']
    list_editable = ['is_approved']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'short_content', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__email', 'receiver__email', 'content']

    def short_content(self, obj):
        return (obj.content[:50] + '...') if len(obj.content) > 50 else obj.content
    short_content.short_description = 'Message'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'short_message', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__email', 'message']

    def short_message(self, obj):
        return (obj.message[:50] + '...') if len(obj.message) > 50 else obj.message
    short_message.short_description = 'Message'