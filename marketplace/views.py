from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from .models import (
    Category, SubCategory, ProductService, ProductImage, 
    PriceList, QuoteRequest, CompanyReview, Message, Notification
)
from .serializers import (
    CategorySerializer, SubCategorySerializer, ProductServiceSerializer,
    ProductImageSerializer, PriceListSerializer, QuoteRequestSerializer,
    CompanyReviewSerializer, MessageSerializer, NotificationSerializer,
    CategoryWithSubcategoriesSerializer
)
from accounts.models import Company, CustomUser
from django_filters import rest_framework as df_filters
from rest_framework.exceptions import ValidationError
from rest_framework import generics

# Custom pagination class
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# Filter classes
class ProductServiceFilter(df_filters.FilterSet):
    min_price = df_filters.NumberFilter(field_name='prices__unit_price', lookup_expr='gte')
    max_price = df_filters.NumberFilter(field_name='prices__unit_price', lookup_expr='lte')
    category = df_filters.ModelChoiceFilter(queryset=Category.objects.all())
    subcategory = df_filters.ModelChoiceFilter(queryset=SubCategory.objects.all())
    company_location = df_filters.CharFilter(field_name='company__location', lookup_expr='icontains')
    is_active = df_filters.BooleanFilter()

    class Meta:
        model = ProductService
        fields = ['type', 'category', 'subcategory', 'min_price', 'max_price', 
                 'company_location', 'is_active']

class QuoteRequestFilter(df_filters.FilterSet):
    status = df_filters.ChoiceFilter(choices=QuoteRequest.STATUS_CHOICES)
    min_quantity = df_filters.NumberFilter(field_name='quantity', lookup_expr='gte')
    max_quantity = df_filters.NumberFilter(field_name='quantity', lookup_expr='lte')

    class Meta:
        model = QuoteRequest
        fields = ['status', 'min_quantity', 'max_quantity']

# Custom permissions
class IsCompanyOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.company.user == request.user

class IsReviewOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user or request.user.is_staff

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_staff

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    @action(detail=True, methods=['get'])
    def subcategories(self, request, pk=None):
        category = self.get_object()
        subcategories = category.subcategories.all()
        serializer = SubCategorySerializer(subcategories, many=True)
        return Response(serializer.data)

class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    filterset_fields = ['category']

class CategoryWithSubcategoriesView(generics.GenericAPIView):
    queryset = Category.objects.all()
    serializer_class = CategoryWithSubcategoriesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get(self, request, *args, **kwargs):
        categories = self.get_queryset()
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)

class ProductServiceViewSet(viewsets.ModelViewSet):
    queryset = ProductService.objects.filter(is_active=True)
    serializer_class = ProductServiceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCompanyOwner]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductServiceFilter
    search_fields = ['name', 'description', 'company__name']
    ordering_fields = ['created_at', 'name', 'prices__unit_price']

    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'company'):
            raise ValidationError("User must have an associated company to create a product.")
        serializer.save(company=self.request.user.company)

    def get_queryset(self):
        queryset = self.queryset
        if self.request.user.is_authenticated and hasattr(self.request.user, 'company'):
            if self.request.user.is_staff:
                return ProductService.objects.all()
            return ProductService.objects.filter(
                Q(company=self.request.user.company) | Q(is_active=True)
            )
        return queryset

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        product = self.get_object()
        if product.company.user != request.user and not request.user.is_staff:
            raise permissions.PermissionDenied(
                "You can only deactivate your own products"
            )
        product.is_active = False
        product.save()
        return Response({'status': 'product deactivated'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        product = self.get_object()
        if product.company.user != request.user and not request.user.is_staff:
            raise permissions.PermissionDenied(
                "You can only activate your own products"
            )
        product.is_active = True
        product.save()
        return Response({'status': 'product activated'})

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCompanyOwner]
    pagination_class = StandardResultsSetPagination

    def perform_create(self, serializer):
        product_service = serializer.validated_data['product_service']
        if product_service.company.user != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied(
                "You can only add images for your own products"
            )
        serializer.save()

    def get_queryset(self):
        queryset = self.queryset
        if self.request.user.is_authenticated and hasattr(self.request.user, 'company'):
            return queryset.filter(
                Q(product_service__company=self.request.user.company) | 
                Q(product_service__is_active=True)
            )
        return queryset.filter(product_service__is_active=True)

class PriceListViewSet(viewsets.ModelViewSet):
    queryset = PriceList.objects.filter(is_active=True)
    serializer_class = PriceListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCompanyOwner]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['product_service', 'is_active']
    ordering_fields = ['unit_price', 'updated_at']

    def perform_create(self, serializer):
        product_service = serializer.validated_data['product_service']
        if product_service.company.user != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied(
                "You can only add prices for your own products"
            )
        serializer.save()

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        price = self.get_object()
        if price.product_service.company.user != request.user and not request.user.is_staff:
            raise permissions.PermissionDenied(
                "You can only deactivate your own prices"
            )
        price.is_active = False
        price.save()
        return Response({'status': 'price deactivated'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        price = self.get_object()
        if price.product_service.company.user != request.user and not request.user.is_staff:
            raise permissions.PermissionDenied(
                "You can only activate your own prices"
            )
        price.is_active = True
        price.save()
        return Response({'status': 'price activated'})

class QuoteRequestViewSet(viewsets.ModelViewSet):
    queryset = QuoteRequest.objects.all()
    serializer_class = QuoteRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = QuoteRequestFilter
    search_fields = ['additional_details', 'product_service__name']
    ordering_fields = ['created_at', 'quantity', 'total_price']

    def perform_create(self, serializer):
        quote = serializer.save(customer=self.request.user)
        Notification.objects.create(
            user=quote.product_service.company.user,
            message=f"New quote request for {quote.product_service.name}",
            notification_type='QUOTE',
            related_quote=quote
        )

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(
            Q(customer=self.request.user) | 
            Q(product_service__company__user=self.request.user)
        )

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        quote = self.get_object()
        if quote.product_service.company.user != request.user and not request.user.is_staff:
            raise permissions.PermissionDenied(
                "You can only accept quotes for your own products"
            )
        quote.status = 'ACCEPTED'
        quote.save()
        Notification.objects.create(
            user=quote.customer,
            message=f"Your quote request for {quote.product_service.name} was accepted",
            notification_type='QUOTE',
            related_quote=quote
        )
        return Response({'status': 'quote accepted'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        quote = self.get_object()
        if quote.product_service.company.user != request.user and not request.user.is_staff:
            raise permissions.PermissionDenied(
                "You can only reject quotes for your own products"
            )
        quote.status = 'REJECTED'
        quote.save()
        Notification.objects.create(
            user=quote.customer,
            message=f"Your quote request for {quote.product_service.name} was rejected",
            notification_type='QUOTE',
            related_quote=quote
        )
        return Response({'status': 'quote rejected'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        quote = self.get_object()
        if quote.customer != request.user and not request.user.is_staff:
            raise permissions.PermissionDenied(
                "You can only cancel your own quotes"
            )
        if quote.status not in ['PENDING', 'ACCEPTED']:
            raise ValidationError("Cannot cancel a quote that is already rejected or cancelled")
        quote.status = 'CANCELLED'
        quote.save()
        Notification.objects.create(
            user=quote.product_service.company.user,
            message=f"Quote request for {quote.product_service.name} was cancelled",
            notification_type='QUOTE',
            related_quote=quote
        )
        return Response({'status': 'quote cancelled'})

class CompanyReviewViewSet(viewsets.ModelViewSet):
    queryset = CompanyReview.objects.filter(is_approved=True)
    serializer_class = CompanyReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsReviewOwnerOrAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['company', 'rating', 'is_approved']
    search_fields = ['comment']
    ordering_fields = ['rating', 'created_at']

    def perform_create(self, serializer):
        review = serializer.save(user=self.request.user)
        if self.request.user.is_staff:
            review.is_approved = True
            review.save()
        else:
            Notification.objects.create(
                user=review.company.user,
                message=f"New review submitted for your company",
                notification_type='REVIEW',
                related_quote=None
            )

    def get_queryset(self):
        if self.request.user.is_staff:
            return CompanyReview.objects.all()
        return CompanyReview.objects.filter(
            Q(user=self.request.user) | 
            Q(company__user=self.request.user) | 
            Q(is_approved=True)
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        review = self.get_object()
        review.is_approved = True
        review.save()
        Notification.objects.create(
            user=review.user,
            message=f"Your review for {review.company.name} has been approved",
            notification_type='REVIEW'
        )
        return Response({'status': 'review approved'})

    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        reviews = CompanyReview.objects.filter(user=request.user)
        page = self.paginate_queryset(reviews)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_read', 'sender', 'receiver']
    search_fields = ['content']
    ordering_fields = ['created_at']

    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)
        Notification.objects.create(
            user=message.receiver,
            message=f"New message from {message.sender.email}",
            notification_type='MESSAGE',
            related_message=message
        )

    def get_queryset(self):
        return self.queryset.filter(
            Q(sender=self.request.user) | Q(receiver=self.request.user)
        )

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        if message.receiver != request.user:
            raise permissions.PermissionDenied(
                "You can only mark your received messages as read"
            )
        message.is_read = True
        message.save()
        return Response({'status': 'message marked as read'})

    @action(detail=False, methods=['get'])
    def conversations(self, request):
        messages = self.get_queryset().values(
            'sender', 'receiver'
        ).distinct()
        return Response(messages)

    @action(detail=False, methods=['get'])
    def unread(self, request):
        messages = self.get_queryset().filter(
            receiver=request.user, 
            is_read=False
        )
        page = self.paginate_queryset(messages)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['notification_type', 'is_read']
    search_fields = ['message']
    ordering_fields = ['created_at']

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'notification marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all notifications marked as read'})

    @action(detail=False, methods=['get'])
    def unread(self, request):
        notifications = self.get_queryset().filter(is_read=False)
        page = self.paginate_queryset(notifications)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)