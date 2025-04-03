from rest_framework import serializers
from .models import (
    Category, SubCategory, ProductService, ProductImage, 
    PriceList, QuoteRequest, CompanyReview, Message, Notification
)
from accounts.models import Company, CustomUser
from rest_framework.validators import UniqueTogetherValidator

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'created_at'
        ]
        read_only_fields = ['slug', 'created_at']

class SubCategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )

    class Meta:
        model = SubCategory
        fields = [
            'id', 'name', 'slug', 'category', 'category_id',
            'description', 'created_at'
        ]
        read_only_fields = ['slug', 'created_at']
        validators = [
            UniqueTogetherValidator(
                queryset=SubCategory.objects.all(),
                fields=['category', 'slug'],
                message='This subcategory slug already exists for this category.'
            )
        ]

class PriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceList
        fields = [
            'id', 'product_service', 'unit_price', 'unit',
            'minimum_quantity', 'description', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price cannot be negative")
        return value

    def validate_minimum_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Minimum quantity must be at least 1")
        return value

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            'id', 'product_service', 'image', 'caption',
            'is_primary', 'created_at'
        ]
        read_only_fields = ['created_at']

class ProductServiceSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    prices = PriceListSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    subcategory = SubCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(),
        source='subcategory',
        write_only=True
    )

    class Meta:
        model = ProductService
        fields = [
            'id', 'company', 'name', 'description', 'category',
            'category_id', 'subcategory', 'subcategory_id',
            'type', 'featured_image', 'is_active', 'images',
            'prices', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        if data['subcategory'].category != data['category']:
            raise serializers.ValidationError(
                "Subcategory must belong to the selected category"
            )
        return data

class CompanyReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    company = serializers.StringRelatedField(read_only=True)
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        source='company',
        write_only=True
    )

    class Meta:
        model = CompanyReview
        fields = [
            'id', 'company', 'company_id', 'user', 'rating',
            'comment', 'is_approved', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at', 'is_approved']
        validators = [
            UniqueTogetherValidator(
                queryset=CompanyReview.objects.all(),
                fields=['company', 'user'],
                message='You have already reviewed this company.'
            )
        ]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

class QuoteRequestSerializer(serializers.ModelSerializer):
    product_service = ProductServiceSerializer(read_only=True)
    customer = serializers.StringRelatedField(read_only=True)
    product_service_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductService.objects.all(),
        source='product_service',
        write_only=True
    )

    class Meta:
        model = QuoteRequest
        fields = [
            'id', 'customer', 'product_service', 'product_service_id',
            'quantity', 'additional_details', 'status', 'total_price',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'customer', 'status', 'total_price',
            'created_at', 'updated_at'
        ]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True)
    receiver = serializers.StringRelatedField(read_only=True)
    receiver_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        source='receiver',
        write_only=True
    )
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Message.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'receiver', 'receiver_id', 'content',
            'parent', 'created_at', 'is_read'
        ]
        read_only_fields = ['sender', 'created_at', 'is_read']

    def validate(self, data):
        if 'parent' in data and data['parent']:
            # Ensure parent message is between the same users
            parent = data['parent']
            sender = self.context['request'].user
            receiver = data['receiver']
            
            if (parent.sender != sender and parent.sender != receiver) or \
               (parent.receiver != sender and parent.receiver != receiver):
                raise serializers.ValidationError(
                    "Parent message must be part of the same conversation"
                )
        return data

class NotificationSerializer(serializers.ModelSerializer):
    related_quote = QuoteRequestSerializer(read_only=True)
    related_message = MessageSerializer(read_only=True)
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'message', 'notification_type',
            'related_quote', 'related_message', 'is_read',
            'created_at'
        ]
        read_only_fields = ['user', 'created_at', 'is_read']