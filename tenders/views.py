from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from datetime import datetime

from .models import (
    Category, SubCategory, ProcurementProcess, AgencyDetails,
    Tender, TenderRequiredDocument, TenderFinancialRequirement,
    TenderTurnoverRequirement, TenderExperienceRequirement,
    TenderPersonnelRequirement, TenderScheduleItem,
    TenderSubscription, NotificationPreference,
    TenderNotification, TenderStatusHistory,
    TenderTechnicalSpecification,
)
from .serializers import (
    CategorySerializer, SubCategorySerializer, CategoryWithSubcategoriesSerializer,
    ProcurementProcessSerializer, AgencyDetailsSerializer, TenderSerializer,
    TenderRequiredDocumentSerializer, TenderFinancialRequirementSerializer,
    TenderTurnoverRequirementSerializer, TenderExperienceRequirementSerializer,
    TenderPersonnelRequirementSerializer, TenderScheduleItemSerializer,
    TenderSubscriptionSerializer, NotificationPreferenceSerializer,
    TenderNotificationSerializer, TenderStatusHistorySerializer,
    TenderTechnicalSpecificationSerializer,
)

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

class ProcurementProcessViewSet(viewsets.ModelViewSet):
    queryset = ProcurementProcess.objects.all()
    serializer_class = ProcurementProcessSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgencyDetailsViewSet(viewsets.ModelViewSet):
    queryset = AgencyDetails.objects.all()
    serializer_class = AgencyDetailsSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.IsAuthenticated]

class TenderViewSet(viewsets.ModelViewSet):
    """
    Full CRUD on Tender plus nested:
      - GET/POST    /tenders/{slug}/required-documents/
      - GET/POST    /tenders/{slug}/financial-requirements/
      - GET/POST    /tenders/{slug}/turnover-requirements/
      - GET/POST    /tenders/{slug}/experience-requirements/
      - GET/POST    /tenders/{slug}/personnel-requirements/
      - GET/POST    /tenders/{slug}/schedule-items/
      - GET/POST    /tenders/{slug}/technical-specifications/
      - POST        /tenders/{slug}/publish/
      - PATCH       /tenders/{slug}/status/
      - POST        /tenders/{slug}/re-advertise/
    """
    queryset = Tender.objects.select_related(
        'category', 'subcategory', 'procurement_process', 'agency', 'created_by'
    ).prefetch_related(
        'required_documents', 'financial_requirements', 'turnover_requirements',
        'experience_requirements', 'personnel_requirements', 'schedule_items',
        'technical_specifications'
    ).all()
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
        tender.save()
        TenderStatusHistory.objects.create(
            tender=tender,
            status=new_status,
            changed_by=self.request.user
        )
        return Response({'detail': f'Status updated to {new_status}.'})

    @action(detail=True, methods=['post'], url_path='re-advertise')
    def re_advertise(self, request, slug=None):
        tender = self.get_object()
        if tender.status not in ['closed', 'cancelled']:
            return Response(
                {'detail': 'Tender must be closed or cancelled to re-advertise.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        new_tender = Tender.objects.create(
            title=tender.title,
            reference_number=f"{tender.reference_number}-R{tender.re_advertisement_count + 1}",
            tenderdescription=tender.tenderdescription,
            category=tender.category,
            subcategory=tender.subcategory,
            procurement_process=tender.procurement_process,
            agency=tender.agency,
            tender_type_country=tender.tender_type_country,
            tender_type_sector=tender.tender_type_sector,
            currency=tender.currency,
            tender_fees=tender.tender_fees,
            source_of_funds=tender.source_of_funds,
            re_advertisement_count=tender.re_advertisement_count + 1,
            publication_date=datetime.strptime(request.data.get('publication_date'), '%Y-%m-%d').date() if request.data.get('publication_date') else timezone.now(),
            submission_deadline=datetime.strptime(request.data.get('submission_deadline'), '%Y-%m-%d').date() if request.data.get('submission_deadline') else None,
            validity_period_days=tender.validity_period_days,
            completion_period_days=tender.completion_period_days,
            allow_alternative_delivery=tender.allow_alternative_delivery,
            litigation_history_start=tender.litigation_history_start,
            litigation_history_end=tender.litigation_history_end,
            tender_document=tender.tender_document,
            tender_securing_type=tender.tender_securing_type,
            tender_security_percentage=tender.tender_security_percentage,
            tender_security_amount=tender.tender_security_amount,
            tender_security_currency=tender.tender_security_currency,
            created_by=self.request.user
        )
        return Response(TenderSerializer(new_tender).data)

    def _nested_list_create(self, request, serializer_class, related_field):
        tender = self.get_object()
        if request.method == 'GET':
            queryset = getattr(tender, related_field).all()
            serializer = serializer_class(queryset, many=True)
            return Response(serializer.data)
        elif request.method == 'POST':
            serializer = serializer_class(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(tender=tender)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

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

    @action(detail=True, methods=['get', 'post'], url_path='technical-specifications')
    def technical_specifications(self, request, slug=None):
        return self._nested_list_create(
            request,
            TenderTechnicalSpecificationSerializer,
            'technical_specifications'
        )

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

class TenderTechnicalSpecificationViewSet(viewsets.ModelViewSet):
    queryset = TenderTechnicalSpecification.objects.all()
    serializer_class = TenderTechnicalSpecificationSerializer
    permission_classes = [permissions.IsAuthenticated]

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