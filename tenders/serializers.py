from rest_framework import serializers
from django.utils import timezone
from .models import (
    Category, SubCategory, ProcurementProcess, Tender, TenderDocument,
    Bid, BidDocument, EvaluationCriterion, EvaluationResponse, Contract, AuditLog
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
        fields = ['id', 'name', 'type', 'description']

class TenderDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField(read_only=True)
    file = serializers.FileField()

    class Meta:
        model = TenderDocument
        fields = ['id', 'tender', 'document_type', 'file', 'version', 'uploaded_by', 'uploaded_at']

class TenderSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
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
            'id', 'title', 'reference_number', 'description', 'category', 'category_id',
            'procurement_process', 'procurement_process_id', 'publication_date',
            'submission_deadline', 'clarification_deadline', 'evaluation_start_date',
            'evaluation_end_date', 'estimated_budget', 'currency', 'bid_bond_percentage',
            'address', 'created_by', 'evaluation_committee', 'status', 'last_status_change',
            'created_at', 'updated_at', 'version', 'documents'
        ]

    def validate(self, data):
        if data['submission_deadline'] <= data['clarification_deadline']:
            raise serializers.ValidationError("Submission deadline must be after clarification deadline.")
        return data

class BidDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField()

    class Meta:
        model = BidDocument
        fields = ['id', 'bid', 'document_type', 'file', 'uploaded_at']

class BidSerializer(serializers.ModelSerializer):
    tender = TenderSerializer(read_only=True)
    tender_id = serializers.PrimaryKeyRelatedField(
        queryset=Tender.objects.all(), source='tender', write_only=True
    )
    bidder = serializers.StringRelatedField(read_only=True)
    documents = BidDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Bid
        fields = [
            'id', 'tender', 'tender_id', 'bidder', 'total_price', 'currency',
            'validity_days', 'technical_score', 'financial_score', 'combined_score',
            'status', 'submission_date', 'documents'
        ]

    def validate(self, data):
        tender = data['tender']
        if tender.status != 'published':
            raise serializers.ValidationError("Cannot submit bid for non-published tender.")
        if tender.submission_deadline < timezone.now():
            raise serializers.ValidationError("Submission deadline has passed.")
        return data

class EvaluationCriterionSerializer(serializers.ModelSerializer):
    tender = TenderSerializer(read_only=True)
    tender_id = serializers.PrimaryKeyRelatedField(
        queryset=Tender.objects.all(), source='tender', write_only=True
    )

    class Meta:
        model = EvaluationCriterion
        fields = ['id', 'tender', 'tender_id', 'name', 'description', 'weight', 'max_score']

class EvaluationResponseSerializer(serializers.ModelSerializer):
    criterion = EvaluationCriterionSerializer(read_only=True)
    criterion_id = serializers.PrimaryKeyRelatedField(
        queryset=EvaluationCriterion.objects.all(), source='criterion', write_only=True
    )
    bid = BidSerializer(read_only=True)
    bid_id = serializers.PrimaryKeyRelatedField(
        queryset=Bid.objects.all(), source='bid', write_only=True
    )
    evaluated_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = EvaluationResponse
        fields = [
            'id', 'criterion', 'criterion_id', 'bid', 'bid_id', 'score',
            'comments', 'evaluated_by', 'evaluated_at'
        ]

class ContractSerializer(serializers.ModelSerializer):
    tender = TenderSerializer(read_only=True)
    tender_id = serializers.PrimaryKeyRelatedField(
        queryset=Tender.objects.all(), source='tender', write_only=True
    )
    bid = BidSerializer(read_only=True)
    bid_id = serializers.PrimaryKeyRelatedField(
        queryset=Bid.objects.all(), source='bid', write_only=True
    )
    signed_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Contract
        fields = [
            'id', 'tender', 'tender_id', 'bid', 'bid_id', 'start_date',
            'end_date', 'value', 'signed_by', 'signed_at'
        ]

    def validate(self, data):
        tender = data['tender']
        if tender.status != 'awarded':
            raise serializers.ValidationError("Cannot create contract for non-awarded tender.")
        return data

class AuditLogSerializer(serializers.ModelSerializer):
    tender = TenderSerializer(read_only=True)
    tender_id = serializers.PrimaryKeyRelatedField(
        queryset=Tender.objects.all(), source='tender', write_only=True
    )
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'tender', 'tender_id', 'user', 'action', 'details', 'timestamp']