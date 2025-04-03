# bids/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import (
    Bid, BidDocument, EvaluationCriterion, EvaluationResponse,
    Contract, AuditLog
)
from tenders.models import Tender
from accounts.models import CustomUser
from tenders.serializers import TenderSerializer
from accounts.serializers import CustomUserSerializer

class BidDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField()

    class Meta:
        model = BidDocument
        fields = ['id', 'bid', 'document_type', 'file', 'uploaded_at']
    
    def validate_file(self, value):
        allowed_types = ['application/pdf', 'application/msword', 'image/jpeg', 'image/png']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Only PDF, Word, JPEG, and PNG files are allowed.")
        max_size = 5 * 1024 * 1024  # 5MB
        if value.size > max_size:
            raise serializers.ValidationError("File size must not exceed 5MB.")
        return value

class BidSerializer(serializers.ModelSerializer):
    tender = TenderSerializer(read_only=True)
    tender_id = serializers.PrimaryKeyRelatedField(
        queryset=Tender.objects.all(), source='tender', write_only=True
    )
    bidder = CustomUserSerializer(read_only=True)
    bidder_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='bidder', write_only=True
    )
    documents = BidDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Bid
        fields = [
            'id', 'tender', 'tender_id', 'bidder', 'bidder_id', 'total_price', 'currency',
            'validity_days', 'technical_score', 'financial_score', 'combined_score',
            'status', 'submission_date', 'documents'
        ]

    def validate(self, data):
        tender = data['tender']
        if tender.status != 'published':
            raise serializers.ValidationError("Cannot submit bid for a non-published tender.")
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

    def validate(self, data):
        if data['weight'] < 0 or data['weight'] > 100:
            raise serializers.ValidationError("Weight must be between 0 and 100.")
        return data

class EvaluationResponseSerializer(serializers.ModelSerializer):
    criterion = EvaluationCriterionSerializer(read_only=True)
    criterion_id = serializers.PrimaryKeyRelatedField(
        queryset=EvaluationCriterion.objects.all(), source='criterion', write_only=True
    )
    bid = BidSerializer(read_only=True)
    bid_id = serializers.UUIDField(source='bid.id', write_only=True)
    evaluated_by = CustomUserSerializer(read_only=True)
    evaluated_by_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='evaluated_by', write_only=True
    )

    class Meta:
        model = EvaluationResponse
        fields = [
            'id', 'criterion', 'criterion_id', 'bid', 'bid_id', 'score',
            'comments', 'evaluated_by', 'evaluated_by_id', 'evaluated_at'
        ]

    def validate(self, data):
        criterion = data['criterion']
        if data['score'] > criterion.max_score:
            raise serializers.ValidationError(f"Score cannot exceed the maximum score of {criterion.max_score}.")
        return data

class ContractSerializer(serializers.ModelSerializer):
    tender = TenderSerializer(read_only=True)
    tender_id = serializers.PrimaryKeyRelatedField(
        queryset=Tender.objects.all(), source='tender', write_only=True
    )
    bid = BidSerializer(read_only=True)
    bid_id = serializers.UUIDField(source='bid.id', write_only=True)
    signed_by = CustomUserSerializer(read_only=True)
    signed_by_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='signed_by', write_only=True, required=False
    )

    class Meta:
        model = Contract
        fields = [
            'id', 'tender', 'tender_id', 'bid', 'bid_id', 'start_date',
            'end_date', 'value', 'signed_by', 'signed_by_id', 'signed_at'
        ]

    def validate(self, data):
        tender = data['tender']
        bid = data['bid']
        if tender.status != 'awarded':
            raise serializers.ValidationError("Cannot create contract for a non-awarded tender.")
        if bid.status != 'awarded':
            raise serializers.ValidationError("Cannot create contract for a non-awarded bid.")
        if bid.tender != tender:
            raise serializers.ValidationError("Bid must belong to the specified tender.")
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("Start date must be before end date.")
        return data

class AuditLogSerializer(serializers.ModelSerializer):
    tender = TenderSerializer(read_only=True)
    tender_id = serializers.PrimaryKeyRelatedField(
        queryset=Tender.objects.all(), source='tender', write_only=True
    )
    user = CustomUserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='user', write_only=True, required=False
    )

    class Meta:
        model = AuditLog
        fields = ['id', 'tender', 'tender_id', 'user', 'user_id', 'action', 'details', 'timestamp']