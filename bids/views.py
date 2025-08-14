from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import (
    Bid, BidDocument, BidFinancialResponse, BidTurnoverResponse,
    BidExperienceResponse, BidPersonnelResponse, BidOfficeResponse,
    BidSourceResponse, BidLitigationResponse, BidScheduleResponse,
    BidTechnicalResponse, BidEvaluation, BidAuditLog
)
from .serializers import (
    BidSerializer, BidDocumentSerializer, BidFinancialResponseSerializer,
    BidTurnoverResponseSerializer, BidExperienceResponseSerializer,
    BidPersonnelResponseSerializer, BidOfficeResponseSerializer,
    BidSourceResponseSerializer, BidLitigationResponseSerializer,
    BidScheduleResponseSerializer, BidTechnicalResponseSerializer,
    BidEvaluationSerializer, BidAuditLogSerializer
)
from tenders.models import Tender

class IsBidderOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user == obj.bidder or request.user.is_staff

class BidViewSet(viewsets.ModelViewSet):
    """
    CRUD for Bids, with submission action.
    """
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [IsBidderOrAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = super().get_queryset()
        tender_id = self.request.query_params.get('tender')
        status = self.request.query_params.get('status')
        if tender_id:
            queryset = queryset.filter(tender_id=tender_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def perform_create(self, serializer):
        tender = serializer.validated_data['tender']
        if tender.submission_deadline < timezone.now():
            raise ValidationError("Cannot create bid: Tender submission deadline has passed.")
        with transaction.atomic():
            bid = serializer.save(bidder=self.request.user)
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='created',
                details=f"Bid created for tender {bid.tender.reference_number}"
            )

    def perform_update(self, serializer):
        if serializer.instance.status != 'draft':
            raise ValidationError("Can only update bids in draft status.")
        tender = serializer.validated_data['tender']
        if tender.submission_deadline < timezone.now():
            raise ValidationError("Cannot update bid: Tender submission deadline has passed.")
        with transaction.atomic():
            bid = serializer.save()
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='updated',
                details=f"Bid updated for tender {bid.tender.reference_number}"
            )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def submit(self, request, pk=None):
        bid = self.get_object()
        if bid.status != 'draft':
            return Response({'error': 'Bid is not in draft status'}, status=400)
        if bid.tender.submission_deadline < timezone.now():
            return Response({'error': 'Tender submission deadline has passed'}, status=400)
        if bid.tender.completion_period_days and not (bid.completion_complied or bid.proposed_completion_days):
            return Response({'error': 'Must comply with completion period or propose an alternative'}, status=400)
        if bid.proposed_completion_days and not bid.tender.allow_alternative_delivery:
            return Response({'error': 'Alternative completion period not allowed'}, status=400)
        required_docs = bid.tender.required_documents.filter(is_required='required')
        if required_docs.count() > bid.bids_documents.count():
            return Response({'error': 'Missing required documents'}, status=400)
        with transaction.atomic():
            bid.status = 'submitted'
            bid.submission_date = timezone.now()
            bid.save()
            BidAuditLog.objects.create(
                bid=bid,
                user=request.user,
                action='submitted',
                details=f"Bid submitted for tender {bid.tender.reference_number}"
            )
        return Response({'status': 'Bid submitted successfully'})

class BidDocumentViewSet(viewsets.ModelViewSet):
    """
    CRUD for BidDocument.
    """
    queryset = BidDocument.objects.all()
    serializer_class = BidDocumentSerializer
    permission_classes = [IsBidderOrAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return BidDocument.objects.filter(bid_id=self.kwargs.get('bid_pk'))

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, pk=self.kwargs.get('bid_pk'))
        if bid.status != 'draft':
            raise ValidationError("Can only add documents to bids in draft status.")
        with transaction.atomic():
            document = serializer.save(bid=bid)
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='document_added',
                details=f"Document {document.tender_document.name} added"
            )

class BidFinancialResponseViewSet(viewsets.ModelViewSet):
    """
    CRUD for BidFinancialResponse.
    """
    queryset = BidFinancialResponse.objects.all()
    serializer_class = BidFinancialResponseSerializer
    permission_classes = [IsBidderOrAdmin]

    def get_queryset(self):
        return BidFinancialResponse.objects.filter(bid_id=self.kwargs.get('bid_pk'))

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, pk=self.kwargs.get('bid_pk'))
        if bid.status != 'draft':
            raise ValidationError("Can only add financial responses to bids in draft status.")
        with transaction.atomic():
            response = serializer.save(bid=bid)
            response.evaluate()
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='financial_response_added',
                details=f"Financial response for {response.financial_requirement.name} added"
            )

class BidTurnoverResponseViewSet(viewsets.ModelViewSet):
    """
    CRUD for BidTurnoverResponse.
    """
    queryset = BidTurnoverResponse.objects.all()
    serializer_class = BidTurnoverResponseSerializer
    permission_classes = [IsBidderOrAdmin]

    def get_queryset(self):
        return BidTurnoverResponse.objects.filter(bid_id=self.kwargs.get('bid_pk'))

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, pk=self.kwargs.get('bid_pk'))
        if bid.status != 'draft':
            raise ValidationError("Can only add turnover responses to bids in draft status.")
        with transaction.atomic():
            response = serializer.save(bid=bid)
            response.evaluate()
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='turnover_response_added',
                details=f"Turnover response for {response.turnover_requirement.label} added"
            )

class BidExperienceResponseViewSet(viewsets.ModelViewSet):
    """
    CRUD for BidExperienceResponse.
    """
    queryset = BidExperienceResponse.objects.all()
    serializer_class = BidExperienceResponseSerializer
    permission_classes = [IsBidderOrAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return BidExperienceResponse.objects.filter(bid_id=self.kwargs.get('bid_pk'))

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, pk=self.kwargs.get('bid_pk'))
        if bid.status != 'draft':
            raise ValidationError("Can only add experience responses to bids in draft status.")
        with transaction.atomic():
            response = serializer.save(bid=bid)
            response.evaluate()
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='experience_response_added',
                details=f"Experience response for {response.experience_requirement.type} added"
            )

class BidPersonnelResponseViewSet(viewsets.ModelViewSet):
    """
    CRUD for BidPersonnelResponse.
    """
    queryset = BidPersonnelResponse.objects.all()
    serializer_class = BidPersonnelResponseSerializer
    permission_classes = [IsBidderOrAdmin]

    def get_queryset(self):
        return BidPersonnelResponse.objects.filter(bid_id=self.kwargs.get('bid_pk'))

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, pk=self.kwargs.get('bid_pk'))
        if bid.status != 'draft':
            raise ValidationError("Can only add personnel responses to bids in draft status.")
        with transaction.atomic():
            response = serializer.save(bid=bid)
            response.evaluate()
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='personnel_response_added',
                details=f"Personnel response for {response.personnel_requirement.role} added"
            )

class BidOfficeResponseViewSet(viewsets.ModelViewSet):
    """
    CRUD for BidOfficeResponse.
    """
    queryset = BidOfficeResponse.objects.all()
    serializer_class = BidOfficeResponseSerializer
    permission_classes = [IsBidderOrAdmin]

    def get_queryset(self):
        return BidOfficeResponse.objects.filter(bid_id=self.kwargs.get('bid_pk'))

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, pk=self.kwargs.get('bid_pk'))
        if bid.status != 'draft':
            raise ValidationError("Can only add office responses to bids in draft status.")
        with transaction.atomic():
            response = serializer.save(bid=bid)
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='office_response_added',
                details=f"Office response for {response.tender_document.name} added"
            )

class BidSourceResponseViewSet(viewsets.ModelViewSet):
    """
    CRUD for BidSourceResponse.
    """
    queryset = BidSourceResponse.objects.all()
    serializer_class = BidSourceResponseSerializer
    permission_classes = [IsBidderOrAdmin]

    def get_queryset(self):
        return BidSourceResponse.objects.filter(bid_id=self.kwargs.get('bid_pk'))

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, pk=self.kwargs.get('bid_pk'))
        if bid.status != 'draft':
            raise ValidationError("Can only add source responses to bids in draft status.")
        with transaction.atomic():
            response = serializer.save(bid=bid)
            response.calculate_total_amount()
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='source_response_added',
                details=f"Source response for {response.tender_document.name} added"
            )

class BidLitigationResponseViewSet(viewsets.ModelViewSet):
    """
    CRUD for BidLitigationResponse.
    """
    queryset = BidLitigationResponse.objects.all()
    serializer_class = BidLitigationResponseSerializer
    permission_classes = [IsBidderOrAdmin]

    def get_queryset(self):
        return BidLitigationResponse.objects.filter(bid_id=self.kwargs.get('bid_pk'))

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, pk=self.kwargs.get('bid_pk'))
        if bid.status != 'draft':
            raise ValidationError("Can only add litigation responses to bids in draft status.")
        with transaction.atomic():
            response = serializer.save(bid=bid)
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='litigation_response_added',
                details=f"Litigation response for {response.tender_document.name} added"
            )

class BidScheduleResponseViewSet(viewsets.ModelViewSet):
    """
    CRUD for BidScheduleResponse.
    """
    queryset = BidScheduleResponse.objects.all()
    serializer_class = BidScheduleResponseSerializer
    permission_classes = [IsBidderOrAdmin]

    def get_queryset(self):
        return BidScheduleResponse.objects.filter(bid_id=self.kwargs.get('bid_pk'))

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, pk=self.kwargs.get('bid_pk'))
        if bid.status != 'draft':
            raise ValidationError("Can only add schedule responses to bids in draft status.")
        with transaction.atomic():
            response = serializer.save(bid=bid)
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='schedule_response_added',
                details=f"Schedule response for {response.schedule_item.commodity} added"
            )

class BidTechnicalResponseViewSet(viewsets.ModelViewSet):
    """
    CRUD for BidTechnicalResponse.
    """
    queryset = BidTechnicalResponse.objects.all()
    serializer_class = BidTechnicalResponseSerializer
    permission_classes = [IsBidderOrAdmin]

    def get_queryset(self):
        return BidTechnicalResponse.objects.filter(bid_id=self.kwargs.get('bid_pk'))

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, pk=self.kwargs.get('bid_pk'))
        if bid.status != 'draft':
            raise ValidationError("Can only add technical responses to bids in draft status.")
        with transaction.atomic():
            response = serializer.save(bid=bid)
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='technical_response_added',
                details=f"Technical response for {response.technical_specification.category} added"
            )

class BidEvaluationViewSet(viewsets.ModelViewSet):
    """
    CRUD for BidEvaluation, admin only.
    """
    queryset = BidEvaluation.objects.all()
    serializer_class = BidEvaluationSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return BidEvaluation.objects.filter(bid_id=self.kwargs.get('bid_pk'))

    def perform_create(self, serializer):
        bid = get_object_or_404(Bid, pk=self.kwargs.get('bid_pk'))
        if bid.status not in ['submitted', 'under_evaluation']:
            raise ValidationError("Can only evaluate bids in submitted or under_evaluation status.")
        with transaction.atomic():
            evaluation = serializer.save(bid=bid, evaluator=self.request.user)
            bid.status = 'under_evaluation'
            bid.save()
            BidAuditLog.objects.create(
                bid=bid,
                user=self.request.user,
                action='evaluated',
                details=f"Evaluation added with score {evaluation.score}"
            )

class BidAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for BidAuditLog, admin only.
    """
    queryset = BidAuditLog.objects.all()
    serializer_class = BidAuditLogSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return BidAuditLog.objects.filter(bid_id=self.kwargs.get('bid_pk'))