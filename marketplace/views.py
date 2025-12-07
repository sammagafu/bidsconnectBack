# marketplace/views.py
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from django_filters import rest_framework as filters

from accounts.permissions import IsCompanyOwner
from rest_framework.permissions import IsAdminUser

from .models import (
    Category, SubCategory, ProductService, ProductImage, PriceList,
    RFQ, RFQItem, Quote, QuoteItem, CompanyReview, Message, Notification
)
from .serializers import (
    CategorySerializer, SubCategorySerializer, ProductServiceSerializer,
    ProductImageSerializer, PriceListSerializer,
    RFQSerializer, RFQItemSerializer,
    QuoteSerializer, QuoteItemSerializer,
    CompanyReviewSerializer, MessageSerializer, NotificationSerializer,
    CategoryWithSubcategoriesSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductServiceFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name='prices__unit_price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='prices__unit_price', lookup_expr='lte')
    category = filters.ModelChoiceFilter(queryset=Category.objects.all())
    subcategory = filters.ModelChoiceFilter(queryset=SubCategory.objects.all())
    company_location = filters.CharFilter(field_name='company__location', lookup_expr='icontains')

    class Meta:
        model = ProductService
        fields = ['type', 'category', 'subcategory', 'is_active']


class RFQFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=RFQ.STATUS_CHOICES)
    class Meta:
        model = RFQ
        fields = ['status']


class QuoteFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=Quote.STATUS_CHOICES)
    class Meta:
        model = Quote
        fields = ['status']


# ViewSets
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']


class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['category']
    search_fields = ['name']


class ProductServiceViewSet(viewsets.ModelViewSet):
    queryset = ProductService.objects.filter(is_active=True)
    serializer_class = ProductServiceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCompanyOwner]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductServiceFilter
    search_fields = ['name', 'description', 'company__name']
    ordering_fields = ['created_at', 'name']

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def get_queryset(self):
        if self.request.user.is_staff:
            return ProductService.objects.all()
        if hasattr(self.request.user, 'company'):
            return ProductService.objects.filter(Q(company=self.request.user.company) | Q(is_active=True))
        return self.queryset


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCompanyOwner]


class PriceListViewSet(viewsets.ModelViewSet):
    queryset = PriceList.objects.all()
    serializer_class = PriceListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCompanyOwner]
    filterset_fields = ['product_service']


class RFQViewSet(viewsets.ModelViewSet):
    queryset = RFQ.objects.all()
    serializer_class = RFQSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RFQFilter

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)


class RFQItemViewSet(viewsets.ModelViewSet):
    queryset = RFQItem.objects.all()
    serializer_class = RFQItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(rfq__buyer=self.request.user)


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner]
    filterset_class = QuoteFilter

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user.company)


class QuoteItemViewSet(viewsets.ModelViewSet):
    queryset = QuoteItem.objects.all()
    serializer_class = QuoteItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner]


class CompanyReviewViewSet(viewsets.ModelViewSet):
    queryset = CompanyReview.objects.filter(is_approved=True)
    serializer_class = CompanyReviewSerializer
    permission_classes = [permissions.IsAuthenticated]


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(Q(sender=self.request.user) | Q(receiver=self.request.user))


# FIXED: Added queryset at class level
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Notification.objects.all()  # ← THIS WAS MISSING
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user).order_by('-created_at')


# Nested creation — perfect
class CategoryWithSubcategoriesView(generics.CreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategoryWithSubcategoriesSerializer
    permission_classes = [IsAdminUser]