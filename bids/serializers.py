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
    TenderPersonnelRequirement, TenderScheduleItem, TenderTechnicalSpecification
)
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
        fields = ['id', 'experience_requirement', 'company_experience', 'complied', 'jv_contribution', 'notes', 'proof']
        read_only_fields = ['id', 'complied']

    def validate(self, attrs):
        if attrs.get('jv_contribution') is not None and (attrs['jv_contribution'] < 0 or attrs['jv_contribution'] > 100):
            raise serializers.ValidationError({"jv_contribution": "JV contribution must be between 0 and 100."})
        return attrs

class BidPersonnelResponseSerializer(serializers.ModelSerializer):
    personnel_requirement = serializers.PrimaryKeyRelatedField(queryset=TenderPersonnelRequirement.objects.all())
    personnel = serializers.PrimaryKeyRelatedField(queryset=CompanyPersonnel.objects.all(), required=False, allow_null=True)

    class Meta:
        model = BidPersonnelResponse
        fields = ['id', 'personnel_requirement', 'personnel', 'complied', 'jv_contribution', 'notes']
        read_only_fields = ['id', 'complied']

    def validate(self, attrs):
        if attrs.get('jv_contribution') is not None and (attrs['jv_contribution'] < 0 or attrs['jv_contribution'] > 100):
            raise serializers.ValidationError({"jv_contribution": "JV contribution must be between 0 and 100."})
        return attrs

class BidOfficeResponseSerializer(serializers.ModelSerializer):
    tender_document = serializers.PrimaryKeyRelatedField(queryset=TenderRequiredDocument.objects.all())
    office = serializers.PrimaryKeyRelatedField(queryset=CompanyOffice.objects.all(), required=False, allow_null=True)

    class Meta:
        model = BidOfficeResponse
        fields = ['id', 'tender_document', 'office', 'notes']
        read_only_fields = ['id']

class BidSourceResponseSerializer(serializers.ModelSerializer):
    tender_document = serializers.PrimaryKeyRelatedField(queryset=TenderRequiredDocument.objects.all())
    sources = serializers.PrimaryKeyRelatedField(queryset=CompanySourceOfFund.objects.all(), many=True)

    class Meta:
        model = BidSourceResponse
        fields = ['id', 'tender_document', 'sources', 'total_amount', 'currency', 'notes']
        read_only_fields = ['id', 'total_amount', 'currency']

    def validate(self, attrs):
        sources = attrs.get('sources', [])
        if sources:
            attrs['total_amount'] = sum(s.amount for s in sources)
            attrs['currency'] = sources[0].currency
        return attrs

class BidLitigationResponseSerializer(serializers.ModelSerializer):
    tender_document = serializers.PrimaryKeyRelatedField(queryset=TenderRequiredDocument.objects.all())
    litigations = serializers.PrimaryKeyRelatedField(queryset=CompanyLitigation.objects.all(), many=True)

    class Meta:
        model = BidLitigationResponse
        fields = ['id', 'tender_document', 'litigations', 'no_litigation', 'notes']
        read_only_fields = ['id']

    def validate(self, attrs):
        if attrs.get('no_litigation') and attrs.get('litigations'):
            raise serializers.ValidationError("Cannot select litigations if 'no_litigation' is checked.")
        return attrs

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
        read_only_fields = ['id']

class BidEvaluationSerializer(serializers.ModelSerializer):
    evaluator = serializers.StringRelatedField()

    class Meta:
        model = BidEvaluation
        fields = ['id', 'evaluator', 'score', 'comments', 'evaluated_at']
        read_only_fields = ['id', 'evaluated_at']

class BidAuditLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = BidAuditLog
        fields = ['id', 'user', 'action', 'details', 'created_at']
        read_only_fields = ['id', 'created_at']

class TenderSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Tender
        fields = ['id', 'title', 'submission_deadline', 'completion_period_days', 'allow_alternative_delivery']

class BidSerializer(serializers.ModelSerializer):
    tender = serializers.PrimaryKeyRelatedField(queryset=Tender.objects.all())
    bidder = serializers.StringRelatedField()
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all())
    jv_partner = serializers.StringRelatedField(allow_null=True)
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
    bids_evaluations = BidEvaluationSerializer(many=True, read_only=True)

    class Meta:
        model = Bid
        fields = [
            'id', 'slug', 'tender', 'bidder', 'company', 'total_price', 'currency',
            'submission_date', 'status', 'validity_complied', 'completion_complied',
            'proposed_completion_days', 'jv_partner', 'jv_percentage', 'created_at',
            'updated_at', 'bids_documents', 'bids_financial_responses',
            'bids_turnover_responses', 'bids_experience_responses',
            'bids_personnel_responses', 'bids_office_responses',
            'bids_source_responses', 'bids_litigation_responses',
            'bids_schedule_responses', 'bids_technical_responses', 'bids_evaluations'
        ]
        read_only_fields = ['id', 'slug', 'submission_date', 'status', 'created_at', 'updated_at']

    def validate(self, attrs):
        tender = attrs.get('tender')
        if tender and tender.completion_period_days:
            if not attrs.get('completion_complied') and not attrs.get('proposed_completion_days'):
                raise serializers.ValidationError({"completion_complied": "Must either comply with completion period or propose an alternative."})
            if attrs.get('proposed_completion_days') and not tender.allow_alternative_delivery:
                raise serializers.ValidationError({"proposed_completion_days": "Alternative completion period not allowed for this tender."})
        if attrs.get('jv_partner') and (attrs.get('jv_percentage') is None or attrs['jv_percentage'] <= 0 or attrs['jv_percentage'] >= 100):
            raise serializers.ValidationError({"jv_percentage": "JV percentage must be between 0 and 100 when a JV partner is specified."})
        return attrs

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
        bid = Bid.objects.create(bidder=self.context['request'].user, **validated_data)
        for doc in nested['bids_documents']:
            BidDocument.objects.create(bid=bid, **doc)
        for fr in nested['bids_financial_responses']:
            BidFinancialResponse.objects.create(bid=bid, **fr).evaluate()
        for tr in nested['bids_turnover_responses']:
            instance = BidTurnoverResponse.objects.create(bid=bid, **tr)
            if tr.get('turnovers'):
                instance.turnovers.set(tr['turnovers'])
            instance.evaluate()
        for er in nested['bids_experience_responses']:
            BidExperienceResponse.objects.create(bid=bid, **er).evaluate()
        for pr in nested['bids_personnel_responses']:
            BidPersonnelResponse.objects.create(bid=bid, **pr).evaluate()
        for or_ in nested['bids_office_responses']:
            BidOfficeResponse.objects.create(bid=bid, **or_)
        for sr in nested['bids_source_responses']:
            instance = BidSourceResponse.objects.create(bid=bid, **sr)
            if sr.get('sources'):
                instance.sources.set(sr['sources'])
            instance.calculate_total_amount()
        for lr in nested['bids_litigation_responses']:
            instance = BidLitigationResponse.objects.create(bid=bid, **lr)
            if lr.get('litigations'):
                instance.litigations.set(lr['litigations'])
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
                BidFinancialResponse.objects.create(bid=instance, **fr).evaluate()
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
                BidExperienceResponse.objects.create(bid=instance, **er).evaluate()
        if nested['bids_personnel_responses'] is not None:
            instance.bids_personnel_responses.all().delete()
            for pr in nested['bids_personnel_responses']:
                BidPersonnelResponse.objects.create(bid=instance, **pr).evaluate()
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