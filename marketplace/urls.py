from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, SubCategoryViewSet, ProductServiceViewSet,
    ProductImageViewSet, PriceListViewSet, QuoteRequestViewSet,
    CompanyReviewViewSet, MessageViewSet, NotificationViewSet
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubCategoryViewSet)
router.register(r'products', ProductServiceViewSet)
router.register(r'product-images', ProductImageViewSet)
router.register(r'prices', PriceListViewSet)
router.register(r'quotes', QuoteRequestViewSet)
router.register(r'reviews', CompanyReviewViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'notifications', NotificationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]