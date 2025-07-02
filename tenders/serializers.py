from rest_framework import serializers
from .models import (
    Category, SubCategory, ProcurementProcess, Tender, TenderDocument,
    TenderSubscription, NotificationPreference, TenderNotification, TenderStatusHistory
)

# Serializer for Category
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

# Serializer for SubCategory
class SubCategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = SubCategory
        fields = ['id', 'category', 'name', 'slug']

# Serializer for ProcurementProcess
class ProcurementProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementProcess
        fields = ['id', 'name', 'slug', 'type']

# Serializer for TenderDocument
class TenderDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderDocument
        fields = ['id', 'tender', 'file', 'uploaded_at']

# Serializer for Tender
class TenderSerializer(serializers.ModelSerializer):
    documents = TenderDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Tender
        fields = ['id', 'reference_number', 'title', 'slug', 'status', 'publication_date', 'submission_deadline', 'created_by', 'created_at', 'updated_at', 'documents']

# Serializer for TenderSubscription
class TenderSubscriptionSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = TenderSubscription
        fields = ['id', 'user', 'category', 'created_at']

# Serializer for NotificationPreference
class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['id', 'user', 'notification_frequency', 'last_notified', 'created_at', 'updated_at']

# Serializer for TenderNotification
class TenderNotificationSerializer(serializers.ModelSerializer):
    tender = TenderSerializer(read_only=True)

    class Meta:
        model = TenderNotification
        fields = ['id', 'user', 'tender', 'message', 'sent_at', 'is_read']

# Serializer for TenderStatusHistory
class TenderStatusHistorySerializer(serializers.ModelSerializer):
    tender = TenderSerializer(read_only=True)

    class Meta:
        model = TenderStatusHistory
        fields = ['id', 'tender', 'status', 'changed_at', 'changed_by']