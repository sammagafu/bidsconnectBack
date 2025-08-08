# tenders/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings

from .models import (
    Category, SubCategory, ProcurementProcess, AgencyDetails,
    Tender, TenderRequiredDocument, TenderFinancialRequirement,
    TenderTurnoverRequirement, TenderExperienceRequirement,
    TenderPersonnelRequirement, TenderScheduleItem,
    TenderSubscription, NotificationPreference,
    TenderNotification, TenderStatusHistory,
    TenderTechnicalSpecification,  # NEW: Import new model
)
from .serializers import (
    CategorySerializer, SubCategorySerializer, CategoryWithSubcategoriesSerializer,
    ProcurementProcessSerializer, AgencyDetailsSerializer, TenderSerializer,
    TenderRequiredDocumentSerializer, TenderFinancialRequirementSerializer,
    TenderTurnoverRequirementSerializer, TenderExperienceRequirementSerializer,
    TenderPersonnelRequirementSerializer, TenderScheduleItemSerializer,
    TenderSubscriptionSerializer, NotificationPreferenceSerializer,
    TenderNotificationSerializer, TenderStatusHistorySerializer,
    TenderTechnicalSpecificationSerializer,  # NEW: Import new serializer
)


# ─── Category & SubCategory ────────────────────────────────────────────────────

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class CategoryWithSubcategoriesViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.prefetch_related('subcategories').all()
    serializer_class = CategoryWithSubcategoriesSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.IsAuthenticated]


# ─── Procurement Process ───────────────────────────────────────────────────────

class ProcurementProcessViewSet(viewsets.ModelViewSet):
    queryset = ProcurementProcess.objects.all()
    serializer_class = ProcurementProcessSerializer
    permission_classes = [permissions.IsAuthenticated]


# ─── Agency Details ──────────────────────────────────────────────────────────

class AgencyDetailsViewSet(viewsets.ModelViewSet):
    queryset = AgencyDetails.objects.all()
    serializer_class = AgencyDetailsSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.IsAuthenticated]


# ─── Tender & Nested Endpoints ─────────────────────────────────────────────────

class TenderViewSet(viewsets.ModelViewSet):
    """
    Full CRUD on Tender plus nested:
      - GET/POST    /tenders/{slug}/required-documents/
      - GET/POST    /tenders/{slug}/financial-requirements/
      - GET/POST    /tenders/{slug}/turnover-requirements/
      - GET/POST    /tenders/{slug}/experience-requirements/
      - GET/POST    /tenders/{slug}/personnel-requirements/
      - GET/POST    /tenders/{slug}/schedule-items/
      - GET/POST    /tenders/{slug}/technical-specifications/  # NEW
      - POST        /tenders/{slug}/publish/
      - PATCH       /tenders/{slug}/status/
    """
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        tender = serializer.save(created_by=self.request.user)
        recipients = [
            s.user.email
            for s in TenderSubscription.objects.filter(category=tender.category)
            if s.user.email
        ]
        if recipients:
            send_mail(
                subject=f'New Tender: {tender.title}',
                message=(
                    f'A new tender "{tender.title}" was posted '
                    f'in category "{tender.category.name}".'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=True,
            )

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, slug=None):
        tender = self.get_object()
        if tender.status != 'draft':
            return Response(
                {'detail': 'Tender already published or closed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        tender.status = 'published'
        tender.publication_date = timezone.now()
        tender.save()
        tender.send_notification_emails()
        return Response({'detail': 'Tender published and notifications sent.'})

    @action(detail=True, methods=['patch'], url_path='status')
    def change_status(self, request, slug=None):
        tender = self.get_object()
        new_status = request.data.get('status')
        valid = [c[0] for c in Tender.STATUS_CHOICES]
        if new_status not in valid:
            return Response(
                {'detail': f'Invalid status "{new_status}".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        tender.status = new_status
        if new_status == 'published' and not tender.publication_date:
            tender.publication_date = timezone.now()
        tender.save()
        return Response({'detail': 'Status updated.', 'status': tender.status})

    def _nested_list_create(self, request, serializer_class, related_name):
        tender = self.get_object()
        if request.method == 'GET':
            qs = getattr(tender, related_name).all()
            page = self.paginate_queryset(qs)
            ser = serializer_class(page or qs, many=True)
            return (
                self.get_paginated_response(ser.data)
                if page is not None else
                Response(ser.data)
            )
        ser = serializer_class(data=request.data)
        if ser.is_valid():
            ser.save(tender=tender)
            return Response(ser.data, status=status.HTTP_201_CREATED)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'], url_path='required-documents')
    def required_documents(self, request, slug=None):
        return self._nested_list_create(
            request,
            TenderRequiredDocumentSerializer,
            'required_documents'
        )

    @action(detail=True, methods=['get', 'post'], url_path='financial-requirements')
    def financial_requirements(self, request, slug=None):
        return self._nested_list_create(
            request,
            TenderFinancialRequirementSerializer,
            'financial_requirements'
        )

    @action(detail=True, methods=['get', 'post'], url_path='turnover-requirements')
    def turnover_requirements(self, request, slug=None):
        return self._nested_list_create(
            request,
            TenderTurnoverRequirementSerializer,
            'turnover_requirements'
        )

    @action(detail=True, methods=['get', 'post'], url_path='experience-requirements')
    def experience_requirements(self, request, slug=None):
        return self._nested_list_create(
            request,
            TenderExperienceRequirementSerializer,
            'experience_requirements'
        )

    @action(detail=True, methods=['get', 'post'], url_path='personnel-requirements')
    def personnel_requirements(self, request, slug=None):
        return self._nested_list_create(
            request,
            TenderPersonnelRequirementSerializer,
            'personnel_requirements'
        )

    @action(detail=True, methods=['get', 'post'], url_path='schedule-items')
    def schedule_items(self, request, slug=None):
        return self._nested_list_create(
            request,
            TenderScheduleItemSerializer,
            'schedule_items'
        )

    @action(detail=True, methods=['get', 'post'], url_path='technical-specifications')  # NEW: Nested endpoint
    def technical_specifications(self, request, slug=None):
        return self._nested_list_create(
            request,
            TenderTechnicalSpecificationSerializer,
            'technical_specifications'
        )


# ─── Flat CRUD on each child type ────────────────────────────────────────────────

class TenderRequiredDocumentViewSet(viewsets.ModelViewSet):
    queryset = TenderRequiredDocument.objects.all()
    serializer_class = TenderRequiredDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]


class TenderFinancialRequirementViewSet(viewsets.ModelViewSet):
    queryset = TenderFinancialRequirement.objects.all()
    serializer_class = TenderFinancialRequirementSerializer
    permission_classes = [permissions.IsAuthenticated]


class TenderTurnoverRequirementViewSet(viewsets.ModelViewSet):
    queryset = TenderTurnoverRequirement.objects.all()
    serializer_class = TenderTurnoverRequirementSerializer
    permission_classes = [permissions.IsAuthenticated]


class TenderExperienceRequirementViewSet(viewsets.ModelViewSet):
    queryset = TenderExperienceRequirement.objects.all()
    serializer_class = TenderExperienceRequirementSerializer
    permission_classes = [permissions.IsAuthenticated]


class TenderPersonnelRequirementViewSet(viewsets.ModelViewSet):
    queryset = TenderPersonnelRequirement.objects.all()
    serializer_class = TenderPersonnelRequirementSerializer
    permission_classes = [permissions.IsAuthenticated]


class TenderScheduleItemViewSet(viewsets.ModelViewSet):
    queryset = TenderScheduleItem.objects.all()
    serializer_class = TenderScheduleItemSerializer
    permission_classes = [permissions.IsAuthenticated]

# NEW: Flat CRUD for new model if needed
class TenderTechnicalSpecificationViewSet(viewsets.ModelViewSet):
    queryset = TenderTechnicalSpecification.objects.all()
    serializer_class = TenderTechnicalSpecificationSerializer
    permission_classes = [permissions.IsAuthenticated]


# ─── Subscriptions & Notifications ─────────────────────────────────────────────

class TenderSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = TenderSubscription.objects.all()
    serializer_class = TenderSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='subscribe')
    def subscribe(self, request):
        cat = request.data.get('category')
        sub, created = TenderSubscription.objects.get_or_create(
            user=request.user,
            category_id=cat,
            defaults={
                'subcategory_id': request.data.get('subcategory'),
                'procurement_process_id': request.data.get('procurement_process'),
                'keywords': request.data.get('keywords', '')
            }
        )
        return Response({'detail': 'Subscribed'},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='unsubscribe')
    def unsubscribe(self, request):
        deleted, _ = TenderSubscription.objects.filter(
            user=request.user,
            category_id=request.data.get('category')
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Not subscribed'}, status=status.HTTP_400_BAD_REQUEST)


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class TenderNotificationViewSet(viewsets.ModelViewSet):
    queryset = TenderNotification.objects.all()
    serializer_class = TenderNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(subscription__user=self.request.user)


class TenderStatusHistoryViewSet(viewsets.ModelViewSet):
    queryset = TenderStatusHistory.objects.all()
    serializer_class = TenderStatusHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(changed_by=self.request.user)

    def get_queryset(self):
        return self.queryset.filter(changed_by=self.request.user)