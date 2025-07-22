from rest_framework import serializers
from .models import (
    Category, SubCategory, ProcurementProcess, AgencyDetails,
    Tender, TenderRequiredDocument,
    TenderSubscription, NotificationPreference, TenderNotification, TenderStatusHistory
)


class SubCategorySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    _destroy = serializers.BooleanField(write_only=True, default=False, required=False)

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'description', '_destroy']
        read_only_fields = ['id']


class CategoryWithSubcategoriesSerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'subcategories']
        read_only_fields = ['id', 'slug']

    def create(self, validated_data):
        subs_data = validated_data.pop('subcategories', [])
        category = Category.objects.create(**validated_data)
        for sub_data in subs_data:
            if sub_data.pop('_destroy', False):
                continue
            SubCategory.objects.create(category=category, **sub_data)
        return category

    def update(self, instance, validated_data):
        subs_data = validated_data.pop('subcategories', [])
        instance.name = validated_data.get('name', instance.name)
        instance.save()

        existing_ids = set(instance.subcategories.values_list('id', flat=True))
        incoming_ids = set()

        for sub_data in subs_data:
            sub_id = sub_data.get('id', None)
            destroy = sub_data.get('_destroy', False)
            if sub_id and destroy:
                SubCategory.objects.filter(id=sub_id, category=instance).delete()
                continue
            sub_data.pop('_destroy', None)
            if sub_id and sub_id in existing_ids:
                obj = instance.subcategories.get(id=sub_id)
                obj.name = sub_data.get('name', obj.name)
                obj.description = sub_data.get('description', obj.description)
                obj.save()
                incoming_ids.add(obj.id)
            else:
                new_obj = SubCategory.objects.create(category=instance, **sub_data)
                incoming_ids.add(new_obj.id)

        to_delete = existing_ids - incoming_ids
        if to_delete:
            SubCategory.objects.filter(id__in=to_delete, category=instance).delete()

        return instance


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']
        read_only_fields = ['id', 'slug']


class ProcurementProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementProcess
        fields = ['id', 'name', 'slug', 'type', 'description']
        read_only_fields = ['id', 'slug']

class AgencyDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgencyDetails
        fields = ['id', 'name', 'slug', 'description', 'logo', 'address', 'phone_number', 'email', 'website', 'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

class TenderRequiredDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderRequiredDocument
        fields = ['id', 'name', 'description', 'document_type']
        read_only_fields = ['id']

class TenderSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    subcategory = SubCategorySerializer(read_only=True)
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), source='subcategory', write_only=True
    )
    procurement_process = ProcurementProcessSerializer(read_only=True)
    procurement_process_id = serializers.PrimaryKeyRelatedField(
        queryset=ProcurementProcess.objects.all(), source='procurement_process', write_only=True
    )
    agency = AgencyDetailsSerializer(read_only=True)
    agency_id = serializers.PrimaryKeyRelatedField(
        queryset=AgencyDetails.objects.all(), source='agency', write_only=True
    )
    created_by = serializers.StringRelatedField(read_only=True)
    required_documents = TenderRequiredDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Tender
        fields = [
            'id', 'slug', 'reference_number', 'title', 'tender_type_country',
            'tender_type_sector', 'tenderdescription',
            'category', 'category_id', 'subcategory', 'subcategory_id',
            'procurement_process', 'procurement_process_id',
            'agency', 'agency_id',
            'publication_date', 'submission_deadline', 'clarification_deadline',
            'evaluation_start_date', 'evaluation_end_date',
            'tender_fees', 'tender_securing_type', 'tender_Security_percentage',
            'tender_Security_amount',
            'status', 'last_status_change', 'version',
            'created_by', 'created_at', 'updated_at',
            'required_documents'
        ]
        read_only_fields = ['id', 'slug', 'status', 'last_status_change',
                            'created_by', 'created_at', 'updated_at']

class TenderSubscriptionSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    subcategory = SubCategorySerializer(read_only=True)
    procurement_process = ProcurementProcessSerializer(read_only=True)

    class Meta:
        model = TenderSubscription
        fields = [
            'id', 'user', 'category', 'subcategory', 'procurement_process',
            'keywords', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['id', 'user', 'email_notifications', 'notification_frequency',
                  'last_notified', 'created_at', 'updated_at']
        read_only_fields = ['id', 'last_notified', 'created_at', 'updated_at']

class TenderNotificationSerializer(serializers.ModelSerializer):
    subscription = TenderSubscriptionSerializer(read_only=True)
    tender = TenderSerializer(read_only=True)

    class Meta:
        model = TenderNotification
        fields = ['id', 'subscription', 'tender', 'sent_at', 'is_sent', 'delivery_status', 'created_at']
        read_only_fields = ['id', 'sent_at', 'is_sent', 'delivery_status', 'created_at']

class TenderStatusHistorySerializer(serializers.ModelSerializer):
    tender = TenderSerializer(read_only=True)
    changed_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TenderStatusHistory
        fields = ['id', 'tender', 'status', 'changed_at', 'changed_by']
        read_only_fields = ['id', 'changed_at', 'changed_by']
