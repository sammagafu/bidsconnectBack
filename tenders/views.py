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
    Award, TenderConversation, TenderMessage, PricingConfig,
)

from bids.models import Bid

from accounts.models import CompanyUser
from .serializers import (
    CategorySerializer, SubCategorySerializer, CategoryWithSubcategoriesSerializer,
    ProcurementProcessSerializer, AgencyDetailsSerializer,
    TenderSerializer, TenderRequiredDocumentSerializer,
    TenderFinancialRequirementSerializer, TenderTurnoverRequirementSerializer,
    TenderExperienceRequirementSerializer, TenderPersonnelRequirementSerializer,
    TenderScheduleItemSerializer, TenderTechnicalSpecificationSerializer,
    TenderSubscriptionSerializer, NotificationPreferenceSerializer,
    TenderNotificationSerializer, TenderStatusHistorySerializer,
    TenderConversationSerializer, TenderMessageSerializer,
    PricingConfigSerializer,
)

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class CanCreateTender(permissions.BasePermission):
    """Allow create/update tenders only for staff or users who are owner/admin of at least one company."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return CompanyUser.objects.filter(
            user=request.user,
            role__in=['owner', 'admin'],
            deleted_at__isnull=True,
            company__deleted_at__isnull=True
        ).exists()


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
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, CanCreateTender]
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

class TenderNotificationViewSet(viewsets.ReadOnlyModelViewSet, viewsets.mixins.UpdateModelMixin):
    queryset = TenderNotification.objects.all()
    serializer_class = TenderNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'head', 'options', 'patch', 'put']

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


class TenderConversationViewSet(viewsets.ModelViewSet):
    """
    Team conversation per company per tender. List/create with ?tender=<slug>.
    Only company members can access their company's conversation.
    """
    serializer_class = TenderConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Count
        company_ids = CompanyUser.objects.filter(
            user=self.request.user, deleted_at__isnull=True
        ).values_list('company_id', flat=True)
        qs = TenderConversation.objects.filter(company_id__in=company_ids).select_related(
            'company', 'tender'
        ).annotate(_message_count=Count('messages'))
        tender_slug = self.request.query_params.get('tender')
        if tender_slug:
            qs = qs.filter(tender__slug=tender_slug)
        return qs

    def create(self, request, *args, **kwargs):
        company = request.user.get_primary_company()
        if not company:
            return Response(
                {"detail": "You must belong to a company to start a tender conversation."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tender = serializer.validated_data.get('tender')
        if not tender:
            return Response(
                {"tender_slug": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        conv, created = TenderConversation.objects.get_or_create(
            company=company, tender=tender,
            defaults={'company': company, 'tender': tender}
        )
        ser = TenderConversationSerializer(conv)
        return Response(ser.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class TenderMessageViewSet(viewsets.ModelViewSet):
    """
    Messages in a tender conversation. Only company members of the conversation can list/post.
    """
    serializer_class = TenderMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        conv_id = self.kwargs.get('conversation_pk')
        conv = get_object_or_404(TenderConversation, pk=conv_id)
        if not CompanyUser.objects.filter(company=conv.company, user=self.request.user, deleted_at__isnull=True).exists():
            return TenderMessage.objects.none()
        return TenderMessage.objects.filter(conversation_id=conv_id).select_related('sender').order_by('created_at')

    def perform_create(self, serializer):
        conv_id = self.kwargs.get('conversation_pk')
        conv = get_object_or_404(TenderConversation, pk=conv_id)
        from rest_framework.exceptions import PermissionDenied
        if not CompanyUser.objects.filter(company=conv.company, user=self.request.user, deleted_at__isnull=True).exists():
            raise PermissionDenied("You are not a member of this conversation's company.")
        serializer.save(conversation=conv, sender=self.request.user)


class IsAdminOrAuthenticatedReadOnly(permissions.BasePermission):
    """Allow GET for any authenticated user; allow write for staff only."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff


class PricingConfigViewSet(viewsets.ModelViewSet):
    """
    List/retrieve platform pricing (tender document fee, tender summary one-time fee).
    Staff can create/update/delete. Used for configurable price caps.
    """
    queryset = PricingConfig.objects.all()
    serializer_class = PricingConfigSerializer
    permission_classes = [IsAdminOrAuthenticatedReadOnly]
    lookup_field = 'fee_type'
    lookup_value_regex = '[^/]+'

    def get_queryset(self):
        qs = PricingConfig.objects.all()
        if not (self.request.user and self.request.user.is_staff):
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only staff can create pricing config.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only staff can update pricing config.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only staff can delete pricing config.")
        instance.is_active = False
        instance.save()