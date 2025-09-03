# bids/serializers.py
from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    Bid, BidDocument, BidFinancialResponse, BidTurnoverResponse,
    BidExperienceResponse, BidPersonnelResponse, BidOfficeResponse,
    BidSourceResponse, BidLitigationResponse, BidScheduleResponse,
    BidTechnicalResponse, BidEvaluation, BidAuditLog
)
from tenders.models import (
    Tender, TenderRequiredDocument, TenderFinancialRequirement,
    TenderTurnoverRequirement, TenderExperienceRequirement,
    TenderPersonnelRequirement, TenderScheduleItem, TenderTechnicalSpecification,
    AgencyDetails
)
from tenders.serializers import TenderSerializer  # Import TenderSerializer for nesting
from accounts.models import (
    CustomUser, Company, CompanyFinancialStatement, CompanyAnnualTurnover,
    CompanyPersonnel, CompanySourceOfFund, CompanyExperience, CompanyOffice,
    CompanyDocument, CompanyCertification, CompanyLitigation
)

class BidDocumentSerializer(serializers.ModelSerializer):
    tender_document = serializers.PrimaryKeyRelatedField(queryset=TenderRequiredDocument.objects.all())
    company_document = serializers.PrimaryKeyRelatedField(queryset=CompanyDocument.objects.all(), required=False, allow_null=True)
    company_certification = serializers.PrimaryKeyRelatedField(queryset=CompanyCertification.objects.all(), required=False, allow_null=True)
    file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = BidDocument
        fields = ['id', 'tender_document', 'company_document', 'company_certification', 'file', 'description', 'submitted_at']
        read_only_fields = ['id', 'submitted_at']

    def validate(self, attrs):
        if not (attrs.get('file') or attrs.get('company_document') or attrs.get('company_certification')):
            raise serializers.ValidationError("At least one of file, company_document, or company_certification must be provided.")
        return attrs

class BidFinancialResponseSerializer(serializers.ModelSerializer):
    financial_requirement = serializers.PrimaryKeyRelatedField(queryset=TenderFinancialRequirement.objects.all())
    financial_statement = serializers.PrimaryKeyRelatedField(queryset=CompanyFinancialStatement.objects.all(), required=False, allow_null=True)

    class Meta:
        model = BidFinancialResponse
        fields = ['id', 'financial_requirement', 'financial_statement', 'actual_value', 'complied', 'jv_contribution', 'notes']
        read_only_fields = ['id', 'complied']

    def validate(self, attrs):
        if attrs.get('jv_contribution') is not None and (attrs['jv_contribution'] < 0 or attrs['jv_contribution'] > 100):
            raise serializers.ValidationError({"jv_contribution": "JV contribution must be between 0 and 100."})
        return attrs

class BidTurnoverResponseSerializer(serializers.ModelSerializer):
    turnover_requirement = serializers.PrimaryKeyRelatedField(queryset=TenderTurnoverRequirement.objects.all())
    turnovers = serializers.PrimaryKeyRelatedField(queryset=CompanyAnnualTurnover.objects.all(), many=True)

    class Meta:
        model = BidTurnoverResponse
        fields = ['id', 'turnover_requirement', 'turnovers', 'actual_amount', 'currency', 'complied', 'jv_contribution', 'notes']
        read_only_fields = ['id', 'complied']

    def validate(self, attrs):
        if attrs.get('jv_contribution') is not None and (attrs['jv_contribution'] < 0 or attrs['jv_contribution'] > 100):
            raise serializers.ValidationError({"jv_contribution": "JV contribution must be between 0 and 100."})
        turnovers = attrs.get('turnovers', [])
        if turnovers:
            attrs['actual_amount'] = sum(t.amount for t in turnovers) / len(turnovers)
            attrs['currency'] = turnovers[0].currency
        return attrs

class BidExperienceResponseSerializer(serializers.ModelSerializer):
    experience_requirement = serializers.PrimaryKeyRelatedField(queryset=TenderExperienceRequirement.objects.all())
    company_experience = serializers.PrimaryKeyRelatedField(queryset=CompanyExperience.objects.all(), required=False, allow_null=True)
    proof = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = BidExperienceResponse
        fields = ['id', 'experience_requirement', 'company_experience', 'proof', 'complied', 'jv_contribution', 'notes']
        read_only_fields = ['id', 'complied']

    def validate(self, attrs):
        if attrs.get('jv_contribution') is not None and (attrs['jv_contribution'] < 0 or attrs['jv_contribution'] > 100):
            raise serializers.ValidationError({"jv_contribution": "JV contribution must be between 0 and 100."})
        return attrs

class BidPersonnelResponseSerializer(serializers.ModelSerializer):
    personnel_requirement = serializers.PrimaryKeyRelatedField(queryset=TenderPersonnelRequirement.objects.all())
    personnels = serializers.PrimaryKeyRelatedField(queryset=CompanyPersonnel.objects.all(), many=True)

    class Meta:
        model = BidPersonnelResponse
        fields = ['id', 'personnel_requirement', 'personnels', 'complied', 'jv_contribution', 'notes']
        read_only_fields = ['id', 'complied']

    def validate(self, attrs):
        if attrs.get('jv_contribution') is not None and (attrs['jv_contribution'] < 0 or attrs['jv_contribution'] > 100):
            raise serializers.ValidationError({"jv_contribution": "JV contribution must be between 0 and 100."})
        return attrs

class BidOfficeResponseSerializer(serializers.ModelSerializer):
    tender_document = serializers.PrimaryKeyRelatedField(queryset=TenderRequiredDocument.objects.all())
    company_office = serializers.PrimaryKeyRelatedField(queryset=CompanyOffice.objects.all(), required=False, allow_null=True)
    proof = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = BidOfficeResponse
        fields = ['id', 'tender_document', 'company_office', 'proof', 'notes']
        read_only_fields = ['id']

    def validate(self, attrs):
        return attrs

class BidSourceResponseSerializer(serializers.ModelSerializer):
    tender_document = serializers.PrimaryKeyRelatedField(queryset=TenderRequiredDocument.objects.all())
    sources = serializers.PrimaryKeyRelatedField(queryset=CompanySourceOfFund.objects.all(), many=True)

    class Meta:
        model = BidSourceResponse
        fields = ['id', 'tender_document', 'sources', 'total_amount', 'currency', 'notes']
        read_only_fields = ['id', 'total_amount', 'currency']

class BidLitigationResponseSerializer(serializers.ModelSerializer):
    tender_document = serializers.PrimaryKeyRelatedField(queryset=TenderRequiredDocument.objects.all())
    litigations = serializers.PrimaryKeyRelatedField(queryset=CompanyLitigation.objects.all(), many=True)

    class Meta:
        model = BidLitigationResponse
        fields = ['id', 'tender_document', 'litigations', 'no_litigation', 'notes']
        read_only_fields = ['id']

class BidScheduleResponseSerializer(serializers.ModelSerializer):
    schedule_item = serializers.PrimaryKeyRelatedField(queryset=TenderScheduleItem.objects.all())

    class Meta:
        model = BidScheduleResponse
        fields = ['id', 'schedule_item', 'proposed_quantity', 'proposed_delivery_date', 'notes']
        read_only_fields = ['id']

class BidTechnicalResponseSerializer(serializers.ModelSerializer):
    technical_specification = serializers.PrimaryKeyRelatedField(queryset=TenderTechnicalSpecification.objects.all())

    class Meta:
        model = BidTechnicalResponse
        fields = ['id', 'technical_specification', 'description', 'complied', 'notes']
        read_only_fields = ['id', 'complied']

class BidEvaluationSerializer(serializers.ModelSerializer):
    bid = serializers.PrimaryKeyRelatedField(read_only=True)
    evaluator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = BidEvaluation
        fields = ['id', 'bid', 'evaluator', 'score', 'comments', 'evaluated_at']
        read_only_fields = ['id', 'evaluated_at']

class BidAuditLogSerializer(serializers.ModelSerializer):
    bid = serializers.PrimaryKeyRelatedField(read_only=True)
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = BidAuditLog
        fields = ['id', 'bid', 'user', 'action', 'details', 'created_at']
        read_only_fields = ['id', 'created_at']

class BidSerializer(serializers.ModelSerializer):
    tender = TenderSerializer(read_only=True)  # Nested for read
    tender_id = serializers.PrimaryKeyRelatedField(queryset=Tender.objects.all(), source='tender', write_only=True)  # PK for write
    bidder = serializers.StringRelatedField(read_only=True)
    company_id = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), source='company', write_only=True)  # PK for write
    bids_documents = BidDocumentSerializer(many=True, required=False)
    bids_financial_responses = BidFinancialResponseSerializer(many=True, required=False)
    bids_turnover_responses = BidTurnoverResponseSerializer(many=True, required=False)
    bids_experience_responses = BidExperienceResponseSerializer(many=True, required=False)
    bids_personnel_responses = BidPersonnelResponseSerializer(many=True, required=False)
    bids_office_responses = BidOfficeResponseSerializer(many=True, required=False)
    bids_source_responses = BidSourceResponseSerializer(many=True, required=False)
    bids_litigation_responses = BidLitigationResponseSerializer(many=True, required=False)
    bids_schedule_responses = BidScheduleResponseSerializer(many=True, required=False)
    bids_technical_responses = BidTechnicalResponseSerializer(many=True, required=False)

    class Meta:
        model = Bid
        fields = [
            'id', 'tender', 'tender_id', 'bidder', 'company_id', 'slug', 'total_price', 'currency',
            'submission_date', 'status', 'validity_complied', 'completion_complied', 'proposed_completion_days',
            'jv_partner', 'jv_percentage', 'created_at', 'updated_at',
            'bids_documents', 'bids_financial_responses', 'bids_turnover_responses',
            'bids_experience_responses', 'bids_personnel_responses', 'bids_office_responses',
            'bids_source_responses', 'bids_litigation_responses', 'bids_schedule_responses',
            'bids_technical_responses'
        ]
        read_only_fields = ['id', 'slug', 'submission_date', 'created_at', 'updated_at', 'bidder']

    def validate(self, data):
        tender = data.get('tender')
        if tender.submission_deadline < timezone.now():
            raise ValidationError("Cannot create/update bid: Tender submission deadline has passed.")
        return data

    def create(self, validated_data):
        nested = {
            'bids_documents': validated_data.pop('bids_documents', []),
            'bids_financial_responses': validated_data.pop('bids_financial_responses', []),
            'bids_turnover_responses': validated_data.pop('bids_turnover_responses', []),
            'bids_experience_responses': validated_data.pop('bids_experience_responses', []),
            'bids_personnel_responses': validated_data.pop('bids_personnel_responses', []),
            'bids_office_responses': validated_data.pop('bids_office_responses', []),
            'bids_source_responses': validated_data.pop('bids_source_responses', []),
            'bids_litigation_responses': validated_data.pop('bids_litigation_responses', []),
            'bids_schedule_responses': validated_data.pop('bids_schedule_responses', []),
            'bids_technical_responses': validated_data.pop('bids_technical_responses', []),
        }
        bid = Bid.objects.create(**validated_data)
        for doc in nested['bids_documents']:
            BidDocument.objects.create(bid=bid, **doc)
        for fr in nested['bids_financial_responses']:
            instance_fr = BidFinancialResponse.objects.create(bid=bid, **fr)
            instance_fr.evaluate()
        for tr in nested['bids_turnover_responses']:
            instance_tr = BidTurnoverResponse.objects.create(bid=bid, **tr)
            if tr.get('turnovers'):
                instance_tr.turnovers.set(tr['turnovers'])
            instance_tr.evaluate()
        for er in nested['bids_experience_responses']:
            instance_er = BidExperienceResponse.objects.create(bid=bid, **er)
            instance_er.evaluate()
        for pr in nested['bids_personnel_responses']:
            instance_pr = BidPersonnelResponse.objects.create(bid=bid, **pr)
            if pr.get('personnels'):
                instance_pr.personnels.set(pr['personnels'])
            instance_pr.evaluate()
        for or_ in nested['bids_office_responses']:
            BidOfficeResponse.objects.create(bid=bid, **or_)
        for sr in nested['bids_source_responses']:
            instance_sr = BidSourceResponse.objects.create(bid=bid, **sr)
            if sr.get('sources'):
                instance_sr.sources.set(sr['sources'])
            instance_sr.calculate_total_amount()
        for lr in nested['bids_litigation_responses']:
            instance_lr = BidLitigationResponse.objects.create(bid=bid, **lr)
            if lr.get('litigations'):
                instance_lr.litigations.set(lr['litigations'])
        for sr in nested['bids_schedule_responses']:
            BidScheduleResponse.objects.create(bid=bid, **sr)
        for tr in nested['bids_technical_responses']:
            BidTechnicalResponse.objects.create(bid=bid, **tr)
        return bid

    def update(self, instance, validated_data):
        nested = {
            'bids_documents': validated_data.pop('bids_documents', None),
            'bids_financial_responses': validated_data.pop('bids_financial_responses', None),
            'bids_turnover_responses': validated_data.pop('bids_turnover_responses', None),
            'bids_experience_responses': validated_data.pop('bids_experience_responses', None),
            'bids_personnel_responses': validated_data.pop('bids_personnel_responses', None),
            'bids_office_responses': validated_data.pop('bids_office_responses', None),
            'bids_source_responses': validated_data.pop('bids_source_responses', None),
            'bids_litigation_responses': validated_data.pop('bids_litigation_responses', None),
            'bids_schedule_responses': validated_data.pop('bids_schedule_responses', None),
            'bids_technical_responses': validated_data.pop('bids_technical_responses', None),
        }
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        if nested['bids_documents'] is not None:
            instance.bids_documents.all().delete()
            for doc in nested['bids_documents']:
                BidDocument.objects.create(bid=instance, **doc)
        if nested['bids_financial_responses'] is not None:
            instance.bids_financial_responses.all().delete()
            for fr in nested['bids_financial_responses']:
                instance_fr = BidFinancialResponse.objects.create(bid=instance, **fr)
                instance_fr.evaluate()
        if nested['bids_turnover_responses'] is not None:
            instance.bids_turnover_responses.all().delete()
            for tr in nested['bids_turnover_responses']:
                instance_tr = BidTurnoverResponse.objects.create(bid=instance, **tr)
                if tr.get('turnovers'):
                    instance_tr.turnovers.set(tr['turnovers'])
                instance_tr.evaluate()
        if nested['bids_experience_responses'] is not None:
            instance.bids_experience_responses.all().delete()
            for er in nested['bids_experience_responses']:
                instance_er = BidExperienceResponse.objects.create(bid=instance, **er)
                instance_er.evaluate()
        if nested['bids_personnel_responses'] is not None:
            instance.bids_personnel_responses.all().delete()
            for pr in nested['bids_personnel_responses']:
                instance_pr = BidPersonnelResponse.objects.create(bid=instance, **pr)
                if pr.get('personnels'):
                    instance_pr.personnels.set(pr['personnels'])
                instance_pr.evaluate()
        if nested['bids_office_responses'] is not None:
            instance.bids_office_responses.all().delete()
            for or_ in nested['bids_office_responses']:
                BidOfficeResponse.objects.create(bid=instance, **or_)
        if nested['bids_source_responses'] is not None:
            instance.bids_source_responses.all().delete()
            for sr in nested['bids_source_responses']:
                instance_sr = BidSourceResponse.objects.create(bid=instance, **sr)
                if sr.get('sources'):
                    instance_sr.sources.set(sr['sources'])
                instance_sr.calculate_total_amount()
        if nested['bids_litigation_responses'] is not None:
            instance.bids_litigation_responses.all().delete()
            for lr in nested['bids_litigation_responses']:
                instance_lr = BidLitigationResponse.objects.create(bid=instance, **lr)
                if lr.get('litigations'):
                    instance_lr.litigations.set(lr['litigations'])
        if nested['bids_schedule_responses'] is not None:
            instance.bids_schedule_responses.all().delete()
            for sr in nested['bids_schedule_responses']:
                BidScheduleResponse.objects.create(bid=instance, **sr)
        if nested['bids_technical_responses'] is not None:
            instance.bids_technical_responses.all().delete()
            for tr in nested['bids_technical_responses']:
                BidTechnicalResponse.objects.create(bid=instance, **tr)
        return instance