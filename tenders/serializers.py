from rest_framework import serializers
from .models import (
    Category, SubCategory, ProcurementProcess, AgencyDetails,
    Tender, TenderRequiredDocument,
    TenderFinancialRequirement, TenderTurnoverRequirement,
    TenderExperienceRequirement, TenderPersonnelRequirement,
    TenderScheduleItem,
    TenderSubscription, NotificationPreference,
    TenderNotification, TenderStatusHistory,
    TenderTechnicalSpecification
)

class SubCategorySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    _destroy = serializers.BooleanField(write_only=True, default=False, required=False)

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'slug', 'category', 'description', '_destroy']
        read_only_fields = ['id']


class CategoryWithSubcategoriesSerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'subcategories']
        read_only_fields = ['id', 'slug']


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
        fields = ['id', 'name', 'formula', 'minimum', 'unit', 'actual_value', 'complied', 'notes', 'jv_compliance', 'financial_sources']
        read_only_fields = ['id', 'complied']


class TenderTurnoverRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderTurnoverRequirement
        fields = ['id', 'label', 'amount', 'currency', 'start_date', 'end_date', 'complied', 'jv_compliance', 'jv_percentage']
        read_only_fields = ['id', 'complied']


class TenderExperienceRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderExperienceRequirement
        fields = [
            'id', 'type', 'description', 'contract_count', 'min_value',
            'currency', 'start_date', 'end_date', 'complied',
            'reputation_notes', 'jv_compliance', 'jv_percentage', 'jv_aggregation_note'
        ]
        read_only_fields = ['id', 'complied']


class TenderPersonnelRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderPersonnelRequirement
        fields = [
            'id', 'role', 'min_education', 'professional_registration',
            'min_experience_yrs', 'appointment_duration_years',
            'nationality_required', 'language_required', 'complied', 'notes',
            'age_min', 'age_max', 'specialized_education', 'professional_certifications', 'jv_compliance'
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
        read_only_fields = ['id']


# ─── Main Tender serializer ─────────────────────────────────────────────────────

class TenderSerializer(serializers.ModelSerializer):
    # nested read/write
    required_documents       = TenderRequiredDocumentSerializer(many=True, required=False)
    financial_requirements   = TenderFinancialRequirementSerializer(many=True, required=False)
    turnover_requirements    = TenderTurnoverRequirementSerializer(many=True, required=False)
    experience_requirements  = TenderExperienceRequirementSerializer(many=True, required=False)
    personnel_requirements   = TenderPersonnelRequirementSerializer(many=True, required=False)
    schedule_items           = TenderScheduleItemSerializer(many=True, required=False)
    technical_specifications = TenderTechnicalSpecificationSerializer(many=True, required=False)

    class Meta:
        model = Tender
        fields = [
            'id', 'title', 'slug', 'reference_number', 'tender_type_country', 'tender_type_sector',
            'currency', 'category', 'subcategory', 'procurement_process', 'agency',
            'description', 'publication_date', 'submission_deadline', 'validity_period_days',
            'completion_period_days', 'litigation_history_start', 'litigation_history_end',
            'tender_document', 'tender_fees', 'tender_securing_type', 'tender_security_percentage',
            'tender_security_amount', 'tender_security_currency', 'status', 'last_status_change',
            'version', 'created_by', 'created_at', 'updated_at', 'allow_alternative_delivery',
            'source_of_funds', 're_advertised_from', 're_advertisement_count',
            'required_documents','financial_requirements','turnover_requirements',
            'experience_requirements','personnel_requirements','schedule_items',
            'technical_specifications'
        ]
        read_only_fields = [
            'id','slug','status','last_status_change',
            'created_by','created_at','updated_at'
        ]

    def create(self, validated_data):
        nested = {
            'required_documents':       validated_data.pop('required_documents', []),
            'financial_requirements':   validated_data.pop('financial_requirements', []),
            'turnover_requirements':    validated_data.pop('turnover_requirements', []),
            'experience_requirements':  validated_data.pop('experience_requirements', []),
            'personnel_requirements':   validated_data.pop('personnel_requirements', []),
            'schedule_items':           validated_data.pop('schedule_items', []),
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
            'required_documents':       validated_data.pop('required_documents', None),
            'financial_requirements':   validated_data.pop('financial_requirements', None),
            'turnover_requirements':    validated_data.pop('turnover_requirements', None),
            'experience_requirements':  validated_data.pop('experience_requirements', None),
            'personnel_requirements':   validated_data.pop('personnel_requirements', None),
            'schedule_items':           validated_data.pop('schedule_items', None),
            'technical_specifications': validated_data.pop('technical_specifications', None),
        }
        # update scalars & FK
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        # wipe & recreate nested if provided
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


# ─── Subscriptions & Notifications ─────────────────────────────────────────────

class TenderSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderSubscription
        fields = ['id','user','category','subcategory','procurement_process','keywords','is_active','created_at','updated_at']
        read_only_fields = ['id','created_at','updated_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['id','user','email_notifications','notification_frequency','last_notified','created_at','updated_at']
        read_only_fields = ['id','last_notified','created_at','updated_at']


class TenderNotificationSerializer(serializers.ModelSerializer):
    subscription = TenderSubscriptionSerializer(read_only=True)
    tender       = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TenderNotification
        fields = ['id','subscription','tender','sent_at','is_sent','delivery_status','created_at']
        read_only_fields = ['id','sent_at','is_sent','delivery_status','created_at']


class TenderStatusHistorySerializer(serializers.ModelSerializer):
    tender     = serializers.PrimaryKeyRelatedField(read_only=True)
    changed_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TenderStatusHistory
        fields = ['id','tender','status','changed_at','changed_by']
        read_only_fields = ['id','changed_at','changed_by']