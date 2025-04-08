from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import (
    Category, SubCategory, ProcurementProcess,
    Tender, TenderDocument, TenderSubscription,
    NotificationPreference, TenderNotification,
    TenderStatusHistory
)
from .serializers import (
    CategorySerializer, SubCategorySerializer, ProcurementProcessSerializer,
    TenderSerializer, TenderDocumentSerializer,
    TenderSubscriptionSerializer, NotificationPreferenceSerializer,
    TenderNotificationSerializer, TenderStatusHistorySerializer
)

# Custom Pagination Class
class TenderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# Category Views
class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()

class CategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'slug'

# SubCategory Views
class SubCategoryListCreateView(generics.ListCreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()

class SubCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'slug'

# ProcurementProcess Views
class ProcurementProcessListCreateView(generics.ListCreateAPIView):
    queryset = ProcurementProcess.objects.all()
    serializer_class = ProcurementProcessSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()

class ProcurementProcessRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProcurementProcess.objects.all()
    serializer_class = ProcurementProcessSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'slug'

# Tender Views
class TenderListCreateView(generics.ListCreateAPIView):
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = [
        'status', 'category__slug', 'subcategory__slug', 'procurement_process__slug',
        # Optional: uncomment to allow filtering by new fields
        'tender_type_country', 'tender_type_sector'
    ]
    search_fields = ['title', 'slug', 'tenderdescription', 'reference_number']
    pagination_class = TenderPagination

    def get_permissions(self):
        # Allow anyone to list tenders (GET), require authentication for creating (POST)
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Staff users see all tenders vacun authenticated
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return queryset
        # Everyone (authenticated or not) sees only published tenders
        return queryset.filter(status='published')

    def perform_create(self, serializer):
        # Only authenticated users can create tenders
        tender = serializer.save(created_by=self.request.user)
        evaluation_committee = self.request.data.get('evaluation_committee', [])
        if evaluation_committee:
            tender.evaluation_committee.set(evaluation_committee)
        TenderStatusHistory.objects.create(
            tender=tender,
            status=tender.status,
            changed_by=self.request.user
        )

class TenderRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer
    permission_classes = [IsAuthenticated,IsAdminUser]
    lookup_field = 'slug'

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        tender = self.get_object()
        if tender.status in ['awarded', 'closed', 'canceled']:
            return Response(
                {"detail": "Cannot modify a completed tender."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_status = self.request.data.get('status', tender.status)
        valid_transitions = {
            'draft': ['pending', 'canceled'],
            'pending': ['published', 'canceled'],
            'published': ['evaluation', 'canceled'],
            'evaluation': ['awarded', 'canceled'],
            'awarded': ['closed'],
            'closed': [],
            'canceled': []
        }
        
        if new_status != tender.status:
            if new_status not in valid_transitions.get(tender.status, []):
                return Response(
                    {"detail": f"Cannot transition from {tender.status} to {new_status}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.save(last_status_change=timezone.now())
            TenderStatusHistory.objects.create(
                tender=tender,
                status=new_status,
                changed_by=self.request.user
            )
        else:
            serializer.save()

    @action(detail=True, methods=['get'])
    def history(self, request, slug=None):
        tender = self.get_object()
        history = tender.status_history.all()
        serializer = TenderStatusHistorySerializer(history, many=True)
        return Response(serializer.data)

# TenderDocument Views
class TenderDocumentListCreateView(generics.ListCreateAPIView):
    queryset = TenderDocument.objects.all()
    serializer_class = TenderDocumentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        tender = get_object_or_404(Tender, id=self.request.data.get('tender'))
        if tender.status not in ['draft', 'pending']:
            return Response(
                {"detail": "Cannot add documents to a tender that is not in draft or pending status."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer.save()

class TenderDocumentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TenderDocument.objects.all()
    serializer_class = TenderDocumentSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

# TenderSubscription Views
class TenderSubscriptionViewSet(ModelViewSet):
    serializer_class = TenderSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        return TenderSubscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, slug=None):
        subscription = self.get_object()
        subscription.is_active = not subscription.is_active
        subscription.save()
        return Response(
            {"detail": f"Subscription {'activated' if subscription.is_active else 'deactivated'}."},
            status=status.HTTP_200_OK
        )

# NotificationPreference Views
class NotificationPreferenceRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

# TenderNotification Views
class TenderNotificationListView(generics.ListAPIView):
    serializer_class = TenderNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TenderNotification.objects.filter(subscription__user=self.request.user)

# Custom API Views
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_tender(request, slug):
    tender = get_object_or_404(Tender, slug=slug)
    if not request.user.is_staff and tender.created_by != request.user:
        return Response(
            {"detail": "You don't have permission to publish this tender."},
            status=status.HTTP_403_FORBIDDEN
        )
    if tender.status not in ['draft', 'pending']:
        return Response(
            {"detail": "Tender cannot be published from its current status."},
            status=status.HTTP_400_BAD_REQUEST
        )
    tender.status = 'published'
    tender.last_status_change = timezone.now()
    tender.save()
    TenderStatusHistory.objects.create(
        tender=tender,
        status='published',
        changed_by=request.user
    )
    return Response({"detail": "Tender published successfully."}, status=status.HTTP_200_OK)