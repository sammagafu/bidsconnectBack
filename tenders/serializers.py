from rest_framework import serializers
from decimal import Decimal
from bids.models import Bid
from .models import (
    Category, SubCategory, ProcurementProcess, AgencyDetails,
    Tender, TenderRequiredDocument,
    TenderFinancialRequirement, TenderTurnoverRequirement,
    TenderExperienceRequirement, TenderPersonnelRequirement,
    TenderScheduleItem, TenderSubscription, NotificationPreference,
    TenderNotification, TenderStatusHistory,
    TenderTechnicalSpecification, Award
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
            sub_id = sub_data.get('id')
            if sub_id and sub_data.pop('_destroy', False):
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

        # delete any omitted
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
        fields = [
            'id', 'name', 'slug', 'description', 'logo',
            'address', 'phone_number', 'email', 'website',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

class TenderRequiredDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderRequiredDocument
        fields = ['id', 'name', 'description', 'document_type', 'is_required']
        read_only_fields = ['id']

class TenderFinancialRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderFinancialRequirement
        fields = [
            'id', 'name', 'formula', 'minimum', 'unit', 'actual_value', 'complied',
            'notes', 'jv_compliance', 'financial_sources'
        ]
        read_only_fields = ['id', 'complied']

class TenderTurnoverRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderTurnoverRequirement
        fields = [
            'id', 'label', 'amount', 'currency', 'start_date', 'end_date',
            'complied', 'jv_compliance', 'jv_percentage'
        ]
        read_only_fields = ['id', 'complied']

class TenderExperienceRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderExperienceRequirement
        fields = [
            'id', 'type', 'description', 'contract_count', 'min_value', 'currency',
            'start_date', 'end_date', 'complied', 'reputation_notes', 'jv_compliance',
            'jv_percentage', 'jv_aggregation_note'
        ]
        read_only_fields = ['id', 'complied']

class TenderPersonnelRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderPersonnelRequirement
        fields = [
            'id', 'role', 'min_education', 'professional_registration', 'min_experience_yrs',
            'appointment_duration_years', 'nationality_required', 'language_required',
            'complied', 'notes', 'age_min', 'age_max', 'specialized_education',
            'professional_certifications', 'jv_compliance'
        ]
        read_only_fields = ['id', 'complied']

class TenderScheduleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderScheduleItem
        fields = ['id', 'commodity', 'code', 'unit', 'quantity', 'specification']
        read_only_fields = ['id']

class TenderTechnicalSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderTechnicalSpecification
        fields = ['id', 'category', 'description', 'complied']
        read_only_fields = ['id', 'complied']

class TenderSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    subcategory = SubCategorySerializer(read_only=True, allow_null=True)
    procurement_process = ProcurementProcessSerializer(read_only=True, allow_null=True)
    agency = AgencyDetailsSerializer(read_only=True, allow_null=True)
    required_documents = TenderRequiredDocumentSerializer(many=True, required=False)
    financial_requirements = TenderFinancialRequirementSerializer(many=True, required=False)
    turnover_requirements = TenderTurnoverRequirementSerializer(many=True, required=False)
    experience_requirements = TenderExperienceRequirementSerializer(many=True, required=False)
    personnel_requirements = TenderPersonnelRequirementSerializer(many=True, required=False)
    schedule_items = TenderScheduleItemSerializer(many=True, required=False)
    technical_specifications = TenderTechnicalSpecificationSerializer(many=True, required=False)
    awarded_bid = serializers.PrimaryKeyRelatedField(read_only=True)

    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, allow_null=True
    )
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), source='subcategory', write_only=True, allow_null=True
    )
    procurement_process_id = serializers.PrimaryKeyRelatedField(
        queryset=ProcurementProcess.objects.all(), source='procurement_process', write_only=True, allow_null=True
    )
    agency_id = serializers.PrimaryKeyRelatedField(
        queryset=AgencyDetails.objects.all(), source='agency', write_only=True, allow_null=True
    )
    awarded_bid_id = serializers.PrimaryKeyRelatedField(
        queryset=Bid.objects.all(), source='awarded_bid', write_only=True, allow_null=True, required=False
    )

    class Meta:
        model = Tender
        fields = [
            'id', 'slug', 'title', 'reference_number', 'description',
            'category', 'category_id', 'subcategory', 'subcategory_id',
            'procurement_process', 'procurement_process_id', 'agency', 'agency_id',
            'status', 'tender_type_country', 'tender_type_sector', 'currency',
            'tender_fees', 'source_of_funds', 'publication_date',
            'submission_deadline', 'validity_period_days', 'completion_period_days',
            'allow_alternative_delivery', 'litigation_history_start', 'litigation_history_end',
            'tender_document', 'tender_securing_type', 'tender_security_percentage',
            'tender_security_amount', 'tender_security_currency', 'version',
            'created_by', 'created_at', 'updated_at', 'last_status_change',
            'awarded_bid', 'awarded_bid_id',
            'required_documents', 'financial_requirements', 'turnover_requirements',
            'experience_requirements', 'personnel_requirements', 'schedule_items',
            'technical_specifications'
        ]
        read_only_fields = [
            'id', 'slug', 'status', 'created_by', 'created_at', 'updated_at',
            'last_status_change', 'version'
        ]

    def validate(self, data):
        if data.get('tender_securing_type') == 'Tender Security':
            if not (data.get('tender_security_percentage') or data.get('tender_security_amount')):
                raise serializers.ValidationError({
                    'tender_securing_type': 'Either tender_security_percentage or tender_security_amount must be provided when tender_securing_type is "Tender Security".'
                })
        return data

    def create(self, validated_data):
        nested = {
            'required_documents': validated_data.pop('required_documents', []),
            'financial_requirements': validated_data.pop('financial_requirements', []),
            'turnover_requirements': validated_data.pop('turnover_requirements', []),
            'experience_requirements': validated_data.pop('experience_requirements', []),
            'personnel_requirements': validated_data.pop('personnel_requirements', []),
            'schedule_items': validated_data.pop('schedule_items', []),
            'technical_specifications': validated_data.pop('technical_specifications', []),
        }
        tender = Tender.objects.create(**validated_data)
        for doc in nested['required_documents']:
            TenderRequiredDocument.objects.create(tender=tender, **doc)
        for fr in nested['financial_requirements']:
            TenderFinancialRequirement.objects.create(tender=tender, **fr)
        for tr in nested['turnover_requirements']:
            TenderTurnoverRequirement.objects.create(tender=tender, **tr)
        for er in nested['experience_requirements']:
            TenderExperienceRequirement.objects.create(tender=tender, **er)
        for pr in nested['personnel_requirements']:
            TenderPersonnelRequirement.objects.create(tender=tender, **pr)
        for si in nested['schedule_items']:
            TenderScheduleItem.objects.create(tender=tender, **si)
        for ts in nested['technical_specifications']:
            TenderTechnicalSpecification.objects.create(tender=tender, **ts)
        return tender

    def update(self, instance, validated_data):
        nested = {
            'required_documents': validated_data.pop('required_documents', None),
            'financial_requirements': validated_data.pop('financial_requirements', None),
            'turnover_requirements': validated_data.pop('turnover_requirements', None),
            'experience_requirements': validated_data.pop('experience_requirements', None),
            'personnel_requirements': validated_data.pop('personnel_requirements', None),
            'schedule_items': validated_data.pop('schedule_items', None),
            'technical_specifications': validated_data.pop('technical_specifications', None),
        }
        # Update scalars & FK
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        # Wipe & recreate nested if provided
        if nested['required_documents'] is not None:
            instance.required_documents.all().delete()
            for doc in nested['required_documents']:
                TenderRequiredDocument.objects.create(tender=instance, **doc)
        if nested['financial_requirements'] is not None:
            instance.financial_requirements.all().delete()
            for fr in nested['financial_requirements']:
                TenderFinancialRequirement.objects.create(tender=instance, **fr)
        if nested['turnover_requirements'] is not None:
            instance.turnover_requirements.all().delete()
            for tr in nested['turnover_requirements']:
                TenderTurnoverRequirement.objects.create(tender=instance, **tr)
        if nested['experience_requirements'] is not None:
            instance.experience_requirements.all().delete()
            for er in nested['experience_requirements']:
                TenderExperienceRequirement.objects.create(tender=instance, **er)
        if nested['personnel_requirements'] is not None:
            instance.personnel_requirements.all().delete()
            for pr in nested['personnel_requirements']:
                TenderPersonnelRequirement.objects.create(tender=instance, **pr)
        if nested['schedule_items'] is not None:
            instance.schedule_items.all().delete()
            for si in nested['schedule_items']:
                TenderScheduleItem.objects.create(tender=instance, **si)
        if nested['technical_specifications'] is not None:
            instance.technical_specifications.all().delete()
            for ts in nested['technical_specifications']:
                TenderTechnicalSpecification.objects.create(tender=instance, **ts)

        return instance

class TenderSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderSubscription
        fields = ['id', 'user', 'category', 'subcategory', 'procurement_process', 'keywords', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['id', 'user', 'email_notifications', 'notification_frequency', 'last_notified', 'created_at', 'updated_at']
        read_only_fields = ['id', 'last_notified', 'created_at', 'updated_at']

class TenderNotificationSerializer(serializers.ModelSerializer):
    subscription = TenderSubscriptionSerializer(read_only=True)
    tender = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TenderNotification
        fields = ['id', 'subscription', 'tender', 'sent_at', 'is_sent', 'delivery_status', 'created_at']
        read_only_fields = ['id', 'sent_at', 'is_sent', 'delivery_status', 'created_at']

class TenderStatusHistorySerializer(serializers.ModelSerializer):
    tender = serializers.PrimaryKeyRelatedField(read_only=True)
    changed_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TenderStatusHistory
        fields = ['id', 'tender', 'status', 'changed_at', 'changed_by']
        read_only_fields = ['id', 'changed_at', 'changed_by']

class AwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Award
        fields = ['id', 'tender', 'awarded_bid', 'awarded_by', 'awarded_date', 'award_document', 'bid_report']
        read_only_fields = ['id']