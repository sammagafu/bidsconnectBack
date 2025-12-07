# marketplace/serializers.py
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

# FIXED: Import both Company and User
from accounts.models import Company, CustomUser as User

from .models import (
    Category, SubCategory, ProductService, ProductImage, PriceList,
    RFQ, RFQItem, Quote, QuoteItem, CompanyReview, Message, Notification
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'created_at']
        read_only_fields = ['slug', 'created_at']


class SubCategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'slug', 'category', 'category_id', 'description', 'created_at']
        read_only_fields = ['slug', 'created_at']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'caption', 'is_primary', 'created_at']
        read_only_fields = ['created_at']


class PriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceList
        fields = ['id', 'unit_price', 'unit', 'minimum_quantity', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ProductServiceSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    prices = PriceListSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    subcategory = SubCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), source='subcategory', write_only=True
    )

    class Meta:
        model = ProductService
        fields = [
            'id', 'company', 'name', 'description', 'category', 'category_id',
            'subcategory', 'subcategory_id', 'type', 'featured_image', 'is_active',
            'images', 'prices', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        subcategory = data.get('subcategory')
        category = data.get('category')
        if subcategory and subcategory.category != category:
            raise serializers.ValidationError("Subcategory must belong to the selected category")
        return data


class RFQItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    subcategory = SubCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, required=False, allow_null=True
    )
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), source='subcategory', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = RFQItem
        fields = [
            'id', 'name', 'description', 'quantity', 'unit', 'type',
            'category', 'category_id', 'subcategory', 'subcategory_id',
            'image', 'created_at'
        ]
        read_only_fields = ['created_at']


class RFQSerializer(serializers.ModelSerializer):
    items = RFQItemSerializer(many=True, read_only=True)
    buyer = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = RFQ
        fields = ['id', 'title', 'buyer', 'status', 'created_at', 'updated_at', 'items']
        read_only_fields = ['title', 'buyer', 'created_at', 'updated_at']


class QuoteItemSerializer(serializers.ModelSerializer):
    rfq_item = RFQItemSerializer(read_only=True)
    rfq_item_id = serializers.PrimaryKeyRelatedField(
        queryset=RFQItem.objects.all(), source='rfq_item', write_only=True
    )

    class Meta:
        model = QuoteItem
        fields = ['id', 'rfq_item', 'rfq_item_id', 'proposed_price', 'details']
        validators = [UniqueTogetherValidator(queryset=QuoteItem.objects.all(), fields=['quote', 'rfq_item'])]


class QuoteSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True, read_only=True)
    rfq = RFQSerializer(read_only=True)
    seller = serializers.StringRelatedField(read_only=True)
    rfq_id = serializers.PrimaryKeyRelatedField(
        queryset=RFQ.objects.all(), source='rfq', write_only=True
    )

    class Meta:
        model = Quote
        fields = ['id', 'rfq', 'rfq_id', 'seller', 'details', 'status', 'created_at', 'updated_at', 'items']
        read_only_fields = ['seller', 'created_at', 'updated_at']


class CompanyReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    company = serializers.StringRelatedField(read_only=True)
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), source='company', write_only=True
    )

    class Meta:
        model = CompanyReview
        fields = ['id', 'company', 'company_id', 'user', 'rating', 'comment', 'is_approved', 'created_at']
        read_only_fields = ['user', 'created_at', 'is_approved']


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True)
    receiver = serializers.StringRelatedField(read_only=True)
    receiver_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='receiver', write_only=True
    )
    related_quote = QuoteSerializer(read_only=True)
    related_quote_id = serializers.PrimaryKeyRelatedField(
        queryset=Quote.objects.all(), source='related_quote', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Message
        fields = ['id', 'sender', 'receiver', 'receiver_id', 'content', 'parent', 'related_quote', 'related_quote_id', 'created_at', 'is_read']
        read_only_fields = ['sender', 'created_at', 'is_read']


class NotificationSerializer(serializers.ModelSerializer):
    related_rfq = RFQSerializer(read_only=True)
    related_quote = QuoteSerializer(read_only=True)
    related_message = MessageSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'notification_type', 'related_rfq', 'related_quote', 'related_message', 'is_read', 'created_at']
        read_only_fields = ['user', 'created_at']


class CategoryWithSubcategoriesSerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'created_at', 'subcategories']
        read_only_fields = ['slug', 'created_at']

    def create(self, validated_data):
        subcategories_data = validated_data.pop('subcategories', [])
        category = Category.objects.create(**validated_data)
        for sub_data in subcategories_data:
            SubCategory.objects.create(category=category, **sub_data)
        return category