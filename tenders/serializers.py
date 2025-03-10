# tenders/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import (
    Category, SubCategory, ProcurementProcess, Tender, TenderDocument,
    TenderSubscription, NotificationPreference, TenderNotification,
    TenderStatusHistory
)
from accounts.models import CustomUser

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class SubCategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'slug', 'category', 'category_id', 'description']

class ProcurementProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementProcess
        fields = ['id', 'name', 'slug', 'type', 'description']

class TenderDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField(read_only=True)
    file = serializers.FileField()

    class Meta:
        model = TenderDocument
        fields = ['id', 'tender', 'file', 'uploaded_at']

    def validate_file(self, value):
        allowed_types = ['application/pdf', 'application/msword', 'image/jpeg', 'image/png']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Only PDF, Word, JPEG, and PNG files are allowed.")
        max_size = 5 * 1024 * 1024  # 5MB
        if value.size > max_size:
            raise serializers.ValidationError("File size must not exceed 5MB.")
        return value

class TenderSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    subcategory = SubCategorySerializer(read_only=True)
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), source='subcategory', write_only=True, required=False
    )
    procurement_process = ProcurementProcessSerializer(read_only=True)
    procurement_process_id = serializers.PrimaryKeyRelatedField(
        queryset=ProcurementProcess.objects.all(), source='procurement_process', write_only=True
    )
    created_by = serializers.StringRelatedField(read_only=True)
    evaluation_committee = serializers.StringRelatedField(many=True, read_only=True)
    documents = TenderDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Tender
        fields = [
            'id', 'title', 'slug', 'reference_number', 'description', 'category', 'category_id',
            'subcategory', 'subcategory_id', 'procurement_process', 'procurement_process_id',
            'publication_date', 'submission_deadline', 'clarification_deadline',
            'evaluation_start_date', 'evaluation_end_date', 'estimated_budget', 'currency',
            'bid_bond_percentage', 'address', 'created_by', 'evaluation_committee', 'status',
            'last_status_change', 'created_at', 'updated_at', 'version', 'documents'
        ]

    def validate(self, data):
        if data['submission_deadline'] <= data['clarification_deadline']:
            raise serializers.ValidationError("Submission deadline must be after clarification deadline.")
        return data

class TenderSubscriptionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, required=False
    )
    subcategory = SubCategorySerializer(read_only=True)
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), source='subcategory', write_only=True, required=False
    )
    procurement_process = ProcurementProcessSerializer(read_only=True)
    procurement_process_id = serializers.PrimaryKeyRelatedField(
        queryset=ProcurementProcess.objects.all(), source='procurement_process', write_only=True, required=False
    )

    class Meta:
        model = TenderSubscription
        fields = [
            'id', 'user', 'slug', 'category', 'category_id', 'subcategory', 'subcategory_id',
            'procurement_process', 'procurement_process_id', 'keywords',
            'created_at', 'updated_at', 'is_active'
        ]

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'email_notifications', 'notification_frequency',
            'last_notified', 'created_at', 'updated_at'
        ]

class TenderNotificationSerializer(serializers.ModelSerializer):
    subscription = TenderSubscriptionSerializer(read_only=True)
    tender = TenderSerializer(read_only=True)

    class Meta:
        model = TenderNotification
        fields = [
            'id', 'subscription', 'tender', 'sent_at', 'is_sent',
            'delivery_status', 'created_at'
        ]

class TenderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TenderStatusHistory
        fields = ['id', 'status', 'changed_at', 'changed_by']