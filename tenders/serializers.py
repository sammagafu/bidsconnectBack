from rest_framework import serializers
from .models import (
    Category, SubCategory, ProcurementProcess, AgencyDetails,
    Tender, TenderRequiredDocument,
    TenderFinancialRequirement, TenderTurnoverRequirement,
    TenderExperienceRequirement, TenderPersonnelRequirement,
    TenderScheduleItem,
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


class TenderFinancialRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderFinancialRequirement
        fields = ['id', 'name', 'formula', 'minimum', 'unit', 'actual_value', 'complied', 'notes']
        read_only_fields = ['id']


class TenderTurnoverRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderTurnoverRequirement
        fields = ['id', 'label', 'amount', 'currency', 'start_date', 'end_date', 'complied']
        read_only_fields = ['id']


class TenderExperienceRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderExperienceRequirement
        fields = ['id', 'type', 'description', 'contract_count', 'min_value', 'currency', 'start_date', 'end_date', 'complied']
        read_only_fields = ['id']


class TenderPersonnelRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderPersonnelRequirement
        fields = ['id', 'role', 'min_education', 'professional_registration', 'min_experience_yrs', 'appointment_duration_years', 'nationality_required', 'language_required', 'complied', 'notes']
        read_only_fields = ['id']


class TenderScheduleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderScheduleItem
        fields = ['id', 'commodity', 'code', 'unit', 'quantity', 'specification']
        read_only_fields = ['id']


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


class TenderSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category', write_only=True)
    subcategory = SubCategorySerializer(read_only=True)
    subcategory_id = serializers.PrimaryKeyRelatedField(queryset=SubCategory.objects.all(), source='subcategory', write_only=True)
    procurement_process = ProcurementProcessSerializer(read_only=True)
    procurement_process_id = serializers.PrimaryKeyRelatedField(queryset=ProcurementProcess.objects.all(), source='procurement_process', write_only=True)
    agency = AgencyDetailsSerializer(read_only=True)
    agency_id = serializers.PrimaryKeyRelatedField(queryset=AgencyDetails.objects.all(), source='agency', write_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    required_documents = TenderRequiredDocumentSerializer(many=True)
    financial_requirements = TenderFinancialRequirementSerializer(many=True)
    turnover_requirements = TenderTurnoverRequirementSerializer(many=True)
    experience_requirements = TenderExperienceRequirementSerializer(many=True)
    personnel_requirements = TenderPersonnelRequirementSerializer(many=True)
    schedule_items = TenderScheduleItemSerializer(many=True)

    class Meta:
        model = Tender
        fields = [
            'id', 'slug', 'reference_number', 'title', 'tender_type_country', 'tender_type_sector', 'tenderdescription',
            'category', 'category_id', 'subcategory', 'subcategory_id', 'procurement_process', 'procurement_process_id', 'agency', 'agency_id',
            'publication_date', 'submission_deadline', 'clarification_deadline', 'evaluation_start_date', 'evaluation_end_date',
            'tender_fees', 'tender_securing_type', 'tender_security_percentage', 'tender_security_amount',
            'status', 'last_status_change', 'version', 'created_by', 'created_at', 'updated_at',
            'required_documents', 'financial_requirements', 'turnover_requirements', 'experience_requirements', 'personnel_requirements', 'schedule_items'
        ]
        read_only_fields = ['id', 'slug', 'status', 'last_status_change', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        docs = validated_data.pop('required_documents', [])
        fin = validated_data.pop('financial_requirements', [])
        turn = validated_data.pop('turnover_requirements', [])
        exp = validated_data.pop('experience_requirements', [])
        pers = validated_data.pop('personnel_requirements', [])
        sched = validated_data.pop('schedule_items', [])
        tender = Tender.objects.create(**validated_data)
        for item in docs:
            TenderRequiredDocument.objects.create(tender=tender, **item)
        for item in fin:
            TenderFinancialRequirement.objects.create(tender=tender, **item)
        for item in turn:
            TenderTurnoverRequirement.objects.create(tender=tender, **item)
        for item in exp:
            TenderExperienceRequirement.objects.create(tender=tender, **item)
        for item in pers:
            TenderPersonnelRequirement.objects.create(tender=tender, **item)
        for item in sched:
            TenderScheduleItem.objects.create(tender=tender, **item)
        return tender

    def update(self, instance, validated_data):
        docs = validated_data.pop('required_documents', None)
        fin = validated_data.pop('financial_requirements', None)
        turn = validated_data.pop('turnover_requirements', None)
        exp = validated_data.pop('experience_requirements', None)
        pers = validated_data.pop('personnel_requirements', None)
        sched = validated_data.pop('schedule_items', None)
        for attr, val in validated_data.items(): setattr(instance, attr, val)
        instance.save()
        if docs is not None:
            instance.required_documents.all().delete()
            for item in docs: TenderRequiredDocument.objects.create(tender=instance, **item)
        if fin is not None:
            instance.financial_requirements.all().delete()
            for item in fin: TenderFinancialRequirement.objects.create(tender=instance, **item)
        if turn is not None:
            instance.turnover_requirements.all().delete()
            for item in turn: TenderTurnoverRequirement.objects.create(tender=instance, **item)
        if exp is not None:
            instance.experience_requirements.all().delete()
            for item in exp: TenderExperienceRequirement.objects.create(tender=instance, **item)
        if pers is not None:
            instance.personnel_requirements.all().delete()
            for item in pers: TenderPersonnelRequirement.objects.create(tender=instance, **item)
        if sched is not None:
            instance.schedule_items.all().delete()
            for item in sched: TenderScheduleItem.objects.create(tender=instance, **item)
        return instance
