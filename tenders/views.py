# views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings

from .models import (
    Category,
    SubCategory,
    ProcurementProcess,
    Tender,
    TenderRequiredDocument,
    TenderSubscription,
    NotificationPreference,
    TenderNotification,
    TenderStatusHistory,
    AgencyDetails,
)
from .serializers import (
    CategorySerializer,
    SubCategorySerializer,
    CategoryWithSubcategoriesSerializer,
    ProcurementProcessSerializer,
    AgencyDetailsSerializer,
    TenderSerializer,
    TenderRequiredDocumentSerializer,
    TenderSubscriptionSerializer,
    NotificationPreferenceSerializer,
    TenderNotificationSerializer,
    TenderStatusHistorySerializer,
)


# ---------------------------
# Category & SubCategory
# ---------------------------

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


# ---------------------------
# Procurement Process
# ---------------------------

class ProcurementProcessViewSet(viewsets.ModelViewSet):
    queryset = ProcurementProcess.objects.all()
    serializer_class = ProcurementProcessSerializer
    permission_classes = [permissions.IsAuthenticated]


# ---------------------------
# Agency Details
# ---------------------------

class AgencyDetailsViewSet(viewsets.ModelViewSet):
    queryset = AgencyDetails.objects.all()
    serializer_class = AgencyDetailsSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'


# ---------------------------
# Tender & Nested Required Documents
# ---------------------------

class TenderViewSet(viewsets.ModelViewSet):
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'

    def perform_create(self, serializer):
        tender = serializer.save(created_by=self.request.user)
        # Notify subscribers in same category
        subs = TenderSubscription.objects.filter(category=tender.category).select_related('user')
        recipients = [sub.user.email for sub in subs if sub.user.email]
        if recipients:
            send_mail(
                subject=f'New Tender: {tender.title}',
                message=f'A new tender "{tender.title}" has been posted in category "{tender.category.name}".',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=True,
            )

    def perform_update(self, serializer):
        serializer.save()

    @action(detail=False, methods=['get'], url_path='subscribed')
    def subscribed(self, request):
        cat_ids = TenderSubscription.objects.filter(user=request.user).values_list('category_id', flat=True)
        qs = self.get_queryset().filter(category_id__in=cat_ids)
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, slug=None):
        tender = self.get_object()
        if tender.status != 'draft':
            return Response({'detail': 'Tender already published or closed.'}, status=status.HTTP_400_BAD_REQUEST)
        tender.status = 'published'
        tender.publication_date = timezone.now()
        tender.save()
        return Response({'detail': 'Tender published successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'post'], url_path='required-documents')
    def required_documents(self, request, slug=None):
        """
        GET  /tenders/{slug}/required-documents/      → list docs for that tender
        POST /tenders/{slug}/required-documents/      → create a new doc for that tender
        """
        tender = self.get_object()

        if request.method == 'GET':
            docs = TenderRequiredDocument.objects.filter(tender=tender)
            page = self.paginate_queryset(docs)
            serializer = TenderRequiredDocumentSerializer(page or docs, many=True)
            if page is not None:
                return self.get_paginated_response(serializer.data)
            return Response(serializer.data)

        # POST to create
        serializer = TenderRequiredDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(tender=tender)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# full CRUD if you ever need direct access
class TenderRequiredDocumentViewSet(viewsets.ModelViewSet):
    queryset = TenderRequiredDocument.objects.all()
    serializer_class = TenderRequiredDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]


# ---------------------------
# Tender Subscription
# ---------------------------

class TenderSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = TenderSubscription.objects.all()
    serializer_class = TenderSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='subscribe')
    def subscribe(self, request):
        cat_id = request.data.get('category')
        sub, created = TenderSubscription.objects.get_or_create(
            user=request.user,
            category_id=cat_id,
            defaults={
                'subcategory_id': request.data.get('subcategory'),
                'procurement_process_id': request.data.get('procurement_process'),
                'keywords': request.data.get('keywords', '')
            }
        )
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response({'detail': 'Subscribed'}, status=code)

    @action(detail=False, methods=['post'], url_path='unsubscribe')
    def unsubscribe(self, request):
        cat_id = request.data.get('category')
        deleted, _ = TenderSubscription.objects.filter(user=request.user, category_id=cat_id).delete()
        if deleted:
            return Response({'detail': 'Unsubscribed'}, status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Not subscribed'}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------
# Notification Preferences
# ---------------------------

class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


# ---------------------------
# Tender Notifications & History
# ---------------------------

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
