# tenders/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from .models import (
    Category, SubCategory, ProcurementProcess, AgencyDetails,
    Tender, TenderRequiredDocument, TenderFinancialRequirement,
    TenderTurnoverRequirement, TenderExperienceRequirement,
    TenderPersonnelRequirement, TenderScheduleItem,
    TenderTechnicalSpecification, TenderSubscription,
    NotificationPreference, TenderNotification, TenderStatusHistory,
    Award
)

from bids.models import Bid

from .serializers import (
    CategorySerializer, SubCategorySerializer, CategoryWithSubcategoriesSerializer,
    ProcurementProcessSerializer, AgencyDetailsSerializer,
    TenderSerializer, TenderRequiredDocumentSerializer,
    TenderFinancialRequirementSerializer, TenderTurnoverRequirementSerializer,
    TenderExperienceRequirementSerializer, TenderPersonnelRequirementSerializer,
    TenderScheduleItemSerializer, TenderTechnicalSpecificationSerializer,
    TenderSubscriptionSerializer, NotificationPreferenceSerializer,
    TenderNotificationSerializer, TenderStatusHistorySerializer
)

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'

class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'

    def get_queryset(self):
        queryset = super().get_queryset()
        category_slug = self.request.query_params.get('category')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)
        return queryset

class CategoryWithSubcategoriesViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategoryWithSubcategoriesSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'

class ProcurementProcessViewSet(viewsets.ModelViewSet):
    queryset = ProcurementProcess.objects.all()
    serializer_class = ProcurementProcessSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'

class AgencyDetailsViewSet(viewsets.ModelViewSet):
    queryset = AgencyDetails.objects.all()
    serializer_class = AgencyDetailsSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    parser_classes = [JSONParser, MultiPartParser, FormParser]

class TenderViewSet(viewsets.ModelViewSet):
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.query_params.get('status')
        category_slug = self.request.query_params.get('category')
        subcategory_slug = self.request.query_params.get('subcategory')
        if status:
            queryset = queryset.filter(status=status)
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)
        if subcategory_slug:
            subcategory = get_object_or_404(SubCategory, slug=subcategory_slug)
            queryset = queryset.filter(subcategory=subcategory)
        return queryset

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise ValidationError("User must be authenticated to create a tender.")
        with transaction.atomic():
            tender = serializer.save(created_by=self.request.user, status='draft')
            TenderStatusHistory.objects.create(tender=tender, status='draft', changed_by=self.request.user)

    def perform_update(self, serializer):
        tender = self.get_object()
        if tender.status not in ['draft', 'pending']:
            raise ValidationError("Can only update tenders in draft or pending status.")
        with transaction.atomic():
            serializer.save()
            if tender.status != serializer.instance.status:
                TenderStatusHistory.objects.create(
                    tender=serializer.instance,
                    status=serializer.instance.status,
                    changed_by=self.request.user
                )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def publish(self, request, slug=None):
        tender = self.get_object()
        if tender.status != 'pending':
            return Response({'error': 'Tender must be in pending status to publish.'}, status=status.HTTP_400_BAD_REQUEST)
        if tender.submission_deadline < timezone.now():
            return Response({'error': 'Submission deadline has passed.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            tender.status = 'published'
            tender.published_date = timezone.now()
            tender.last_status_change = timezone.now()
            tender.save()
            TenderStatusHistory.objects.create(tender=tender, status='published', changed_by=request.user)
        return Response({'status': 'Tender published successfully.'})

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAdminUser], url_path='status')
    def update_status(self, request, slug=None):
        tender = self.get_object()
        new_status = request.data.get('status')
        if new_status not in [choice[0] for choice in Tender.STATUS_CHOICES]:
            return Response({'error': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)
        if new_status == tender.status:
            return Response({'error': 'Status unchanged.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            old_status = tender.status
            tender.status = new_status
            tender.last_status_change = timezone.now()
            tender.save()
            TenderStatusHistory.objects.create(tender=tender, status=new_status, changed_by=request.user)
            if new_status == 'published' and old_status != 'published':
                tender.published_date = timezone.now()
                tender.save()
        return Response({'status': f'Tender status updated to {new_status}.'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser], url_path='award')
    def award(self, request, slug=None):
        tender = self.get_object()
        if tender.status != 'evaluation':
            return Response({'error': 'Can only award tenders in evaluation status.'}, status=status.HTTP_400_BAD_REQUEST)
        bid_id = request.data.get('bid_id')
        if not bid_id:
            return Response({'error': 'bid_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            bid = Bid.objects.get(id=bid_id, tender=tender)  # Ensure bid belongs to this tender
        except Bid.DoesNotExist:
            return Response({'error': 'Invalid bid_id or bid not associated with this tender.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            award, created = Award.objects.get_or_create(tender=tender)
            award.awarded_bid = bid
            award.awarded_by = request.user
            award.awarded_date = timezone.now()
            if 'award_document' in request.FILES:
                award.award_document = request.FILES['award_document']
            if 'bid_report' in request.FILES:
                award.bid_report = request.FILES['bid_report']
            award.save()
            tender.awarded_bid = bid
            tender.status = 'awarded'
            tender.last_status_change = timezone.now()
            tender.save()
            TenderStatusHistory.objects.create(tender=tender, status='awarded', changed_by=request.user)
        return Response({'status': 'Tender awarded successfully.'})

class TenderRequiredDocumentViewSet(viewsets.ModelViewSet):
    queryset = TenderRequiredDocument.objects.all()
    serializer_class = TenderRequiredDocumentSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        tender_slug = self.request.query_params.get('tender')
        if tender_slug:
            tender = get_object_or_404(Tender, slug=tender_slug)
            queryset = queryset.filter(tender=tender)
        return queryset

class TenderFinancialRequirementViewSet(viewsets.ModelViewSet):
    queryset = TenderFinancialRequirement.objects.all()
    serializer_class = TenderFinancialRequirementSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        tender_slug = self.request.query_params.get('tender')
        if tender_slug:
            tender = get_object_or_404(Tender, slug=tender_slug)
            queryset = queryset.filter(tender=tender)
        return queryset

class TenderTurnoverRequirementViewSet(viewsets.ModelViewSet):
    queryset = TenderTurnoverRequirement.objects.all()
    serializer_class = TenderTurnoverRequirementSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        tender_slug = self.request.query_params.get('tender')
        if tender_slug:
            tender = get_object_or_404(Tender, slug=tender_slug)
            queryset = queryset.filter(tender=tender)
        return queryset

class TenderExperienceRequirementViewSet(viewsets.ModelViewSet):
    queryset = TenderExperienceRequirement.objects.all()
    serializer_class = TenderExperienceRequirementSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        tender_slug = self.request.query_params.get('tender')
        if tender_slug:
            tender = get_object_or_404(Tender, slug=tender_slug)
            queryset = queryset.filter(tender=tender)
        return queryset

class TenderPersonnelRequirementViewSet(viewsets.ModelViewSet):
    queryset = TenderPersonnelRequirement.objects.all()
    serializer_class = TenderPersonnelRequirementSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        tender_slug = self.request.query_params.get('tender')
        if tender_slug:
            tender = get_object_or_404(Tender, slug=tender_slug)
            queryset = queryset.filter(tender=tender)
        return queryset

class TenderScheduleItemViewSet(viewsets.ModelViewSet):
    queryset = TenderScheduleItem.objects.all()
    serializer_class = TenderScheduleItemSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        tender_slug = self.request.query_params.get('tender')
        if tender_slug:
            tender = get_object_or_404(Tender, slug=tender_slug)
            queryset = queryset.filter(tender=tender)
        return queryset

class TenderTechnicalSpecificationViewSet(viewsets.ModelViewSet):
    queryset = TenderTechnicalSpecification.objects.all()
    serializer_class = TenderTechnicalSpecificationSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        tender_slug = self.request.query_params.get('tender')
        if tender_slug:
            tender = get_object_or_404(Tender, slug=tender_slug)
            queryset = queryset.filter(tender=tender)
        return queryset

class TenderSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = TenderSubscription.objects.all()
    serializer_class = TenderSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        try:
            return NotificationPreference.objects.get(user=self.request.user)
        except ObjectDoesNotExist:
            raise ValidationError("Notification preferences not found for this user.")

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        if NotificationPreference.objects.filter(user=self.request.user).exists():
            raise ValidationError("Notification preferences already exist for this user.")
        serializer.save(user=self.request.user)

class TenderNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TenderNotification.objects.all()
    serializer_class = TenderNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(subscription__user=self.request.user)

class TenderStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TenderStatusHistory.objects.all()
    serializer_class = TenderStatusHistorySerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()
        tender_slug = self.request.query_params.get('tender')
        if tender_slug:
            tender = get_object_or_404(Tender, slug=tender_slug)
            queryset = queryset.filter(tender=tender)
        return queryset