# tenders/views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import (
    Category, SubCategory, ProcurementProcess,
    Tender, TenderDocument, TenderSubscription,
    NotificationPreference, TenderNotification
)
from .serializers import (
    CategorySerializer, SubCategorySerializer, ProcurementProcessSerializer,
    TenderSerializer, TenderDocumentSerializer,
    # BidSerializer, BidDocumentSerializer, EvaluationCriterionSerializer,
    # EvaluationResponseSerializer, ContractSerializer, AuditLogSerializer
)

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

# Tender Views
class TenderListCreateView(generics.ListCreateAPIView):
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter tenders based on status for non-admin users
        if not self.request.user.is_staff:
            queryset = queryset.filter(status='published')
        # Add search functionality
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(reference_number__icontains=search_query)
            )
        return queryset

    def perform_create(self, serializer):
        # Set created_by to the current user
        tender = serializer.save(created_by=self.request.user)
        # Add the creator to the evaluation committee if specified
        evaluation_committee = self.request.data.get('evaluation_committee', [])
        if evaluation_committee:
            tender.evaluation_committee.set(evaluation_committee)

class TenderRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        tender = self.get_object()
        # Prevent updates to completed tenders
        if tender.status in ['awarded', 'closed', 'canceled']:
            return Response(
                {"detail": "Cannot modify a completed tender."},
                status=status.HTTP_403_FORBIDDEN
            )
        # Handle status changes
        new_status = self.request.data.get('status', tender.status)
        if new_status != tender.status and new_status in ['published', 'canceled']:
            serializer.save(last_status_change=timezone.now())
        else:
            serializer.save()

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
        serializer.save(uploaded_by=self.request.user)

class TenderDocumentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TenderDocument.objects.all()
    serializer_class = TenderDocumentSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

# TenderSubscription Views
class TenderSubscriptionListCreateView(generics.ListCreateAPIView):
    serializer_class = TenderSubscriptionSerializer  # You'll need to create this serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TenderSubscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TenderSubscriptionRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TenderSubscriptionSerializer  # You'll need to create this serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TenderSubscription.objects.filter(user=self.request.user)

# NotificationPreference Views
class NotificationPreferenceRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer  # You'll need to create this serializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

# TenderNotification Views
class TenderNotificationListView(generics.ListAPIView):
    serializer_class = TenderNotificationSerializer  # You'll need to create this serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TenderNotification.objects.filter(subscription__user=self.request.user)

# Custom API Views
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_tender(request, pk):
    tender = get_object_or_404(Tender, pk=pk)
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
    return Response({"detail": "Tender published successfully."}, status=status.HTTP_200_OK)

# Serializers that need to be added to serializers.py
from .models import TenderSubscription, NotificationPreference, TenderNotification

class TenderSubscriptionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, required=False
    )
    subcategory = SubCategorySerializer(read_only=True)
    subcategory_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), source='subcategory', write_only=True, required=False
    )
    procurement_process = ProcurementProcessSerializer(read_only=True)
    procurement_process_id = serializers.PrimaryKeyRelatedField(
        queryset=ProcurementProcess.objects.all(), source='procurement_process', write_only=True, required=False
    )

    class Meta:
        model = TenderSubscription
        fields = [
            'id', 'user', 'category', 'category_id', 'subcategory', 'subcategory_id',
            'procurement_process', 'procurement_process_id', 'keywords',
            'created_at', 'updated_at', 'is_active'
        ]

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'email_notifications', 'notification_frequency',
            'last_notified', 'created_at', 'updated_at'
        ]

class TenderNotificationSerializer(serializers.ModelSerializer):
    subscription = TenderSubscriptionSerializer(read_only=True)
    tender = TenderSerializer(read_only=True)

    class Meta:
        model = TenderNotification
        fields = [
            'id', 'subscription', 'tender', 'sent_at', 'is_sent',
            'delivery_status', 'created_at'
        ]