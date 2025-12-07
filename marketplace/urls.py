# marketplace/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, SubCategoryViewSet, ProductServiceViewSet,
    ProductImageViewSet, PriceListViewSet, RFQViewSet, RFQItemViewSet,
    QuoteViewSet, QuoteItemViewSet, CompanyReviewViewSet,
    MessageViewSet, NotificationViewSet,
    CategoryWithSubcategoriesView
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubCategoryViewSet)
router.register(r'products-services', ProductServiceViewSet)
router.register(r'product-images', ProductImageViewSet)
router.register(r'prices', PriceListViewSet)
router.register(r'rfqs', RFQViewSet)
router.register(r'rfq-items', RFQItemViewSet)
router.register(r'quotes', QuoteViewSet)
router.register(r'quote-items', QuoteItemViewSet)
router.register(r'reviews', CompanyReviewViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'notifications', NotificationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('categories-with-subcategories/', CategoryWithSubcategoriesView.as_view(), name='categories-with-subcategories'),
]