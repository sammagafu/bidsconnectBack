from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import FileResponse
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

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

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
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = super().get_queryset()
        tender_id = self.request.query_params.get('tender')
        status = self.request.query_params.get('status')
        company_id = self.request.query_params.get('company_id')
        if tender_id:
            queryset = queryset.filter(tender_id=tender_id)
        if status:
            queryset = queryset.filter(status=status)
        if company_id:
            queryset = queryset.filter(company_id=company_id)
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

    @action(detail=True, methods=['patch'], url_path='reject')
    def reject(self, request, pk=None):
        bid = self.get_object()
        if bid.status in ['rejected', 'accepted']:
            raise ValidationError("Bid already finalized.")
        bid.status = 'rejected'
        bid.save()
        return Response({'status': 'Bid rejected'})

    @action(detail=False, methods=['get'], url_path='by-company')
    def by_company(self, request):
        company_id = request.query_params.get('company_id')
        if not company_id:
            raise ValidationError("company_id is required")
        queryset = self.get_queryset().filter(company_id=company_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def submit(self, request, pk=None):
        bid = self.get_object()
        # Reuse validation logic
        validation_response = self.validate_submit(request, pk)
        if not validation_response.data['is_ready']:
            return Response({'error': '; '.join(validation_response.data['errors'])}, status=400)
        
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

    @action(detail=True, methods=['get'], url_path='validate-submit')
    def validate_submit(self, request, pk=None):
        bid = self.get_object()
        errors = []

        # Check status
        if bid.status != 'draft':
            errors.append('Bid is not in draft status')

        # Check deadline
        if bid.tender.submission_deadline < timezone.now():
            errors.append('Tender submission deadline has passed')

        # Check completion compliance
        if bid.tender.completion_period_days and not (bid.completion_complied or bid.proposed_completion_days):
            errors.append('Must comply with completion period or propose an alternative')

        # Check alternative delivery allowance
        if bid.proposed_completion_days and not bid.tender.allow_alternative_delivery:
            errors.append('Alternative completion period not allowed for this tender')

        # Check JV if applicable
        if bid.jv_partner and (bid.jv_percentage is None or bid.jv_percentage <= 0 or bid.jv_percentage >= 100):
            errors.append('JV percentage must be between 0 and 100 when a JV partner is specified')

        # Check required documents
        required_docs = bid.tender.required_documents.filter(is_required=True)
        submitted_doc_ids = bid.bids_documents.values_list('tender_document__id', flat=True)
        missing_docs = required_docs.exclude(id__in=submitted_doc_ids)
        if missing_docs.exists():
            missing_names = list(missing_docs.values_list('name', flat=True))
            errors.append(f'Missing required documents: {", ".join(missing_names)}')

        # Log the validation
        logger.info(f"Validated bid {bid.id} for user {request.user.id}: is_ready={not bool(errors)}, errors={errors}")

        if errors:
            return Response({
                'is_ready': False,
                'errors': errors
            }, status=200)

        return Response({'is_ready': True}, status=200)

    @action(detail=True, methods=['get'], url_path='opening-report')
    def opening_report(self, request, pk=None):
        bid = self.get_object()
        if bid.status not in ['submitted', 'under_evaluation', 'accepted', 'rejected']:
            raise ValidationError("Opening report is only available for submitted or evaluated bids.")

        # Generate PDF in memory
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Header
        p.drawString(100, height - 100, f"Bid Opening Report for {bid.tender.title}")
        p.drawString(100, height - 120, f"Reference: {bid.tender.reference_number}")
        p.drawString(100, height - 140, f"Bidder: {bid.company.name}")
        p.drawString(100, height - 160, f"Status: {bid.status.upper()}")
        p.drawString(100, height - 180, f"Total Price: {bid.total_price} {bid.currency}")
        p.drawString(100, height - 200, f"Submission Date: {bid.submission_date}")
        p.drawString(100, height - 220, f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Documents section
        y = height - 240
        p.drawString(100, y, "Submitted Documents:")
        y -= 20
        for doc in bid.bids_documents.all():
            p.drawString(100, y, f"- {doc.tender_document.name} (Submitted at {doc.submitted_at})")
            y -= 20
            if y < 100:  # Simple page break
                p.showPage()
                y = height - 100

        # Add more sections as needed (e.g., financial responses)
        p.drawString(100, y, "Financial Responses:")
        y -= 20
        for fr in bid.bids_financial_responses.all():
            p.drawString(100, y, f"- {fr.financial_requirement.name}: {fr.actual_value} (Complied: {fr.complied})")
            y -= 20
            if y < 100:
                p.showPage()
                y = height - 100

        p.save()
        buffer.seek(0)

        # Return the PDF
        return FileResponse(buffer, as_attachment=False, filename=f"bid_{bid.slug}_opening_report.pdf", content_type='application/pdf')

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