from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, SubCategoryViewSet, ProcurementProcessViewSet, TenderViewSet,
    TenderDocumentViewSet, TenderSubscriptionViewSet, NotificationPreferenceViewSet,
    TenderNotificationViewSet, CategoriesWithSubcategoriesView
)

# Create a router and register viewsets
router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubCategoryViewSet)
router.register(r'procurement-processes', ProcurementProcessViewSet)
router.register(r'tenders', TenderViewSet)
router.register(r'tender-documents', TenderDocumentViewSet)
router.register(r'subscriptions', TenderSubscriptionViewSet)
router.register(r'notification-preferences', NotificationPreferenceViewSet)
router.register(r'notifications', TenderNotificationViewSet)

# Define URL patterns
urlpatterns = [
    path('', include(router.urls)),
    path('categories-with-subcategories/', CategoriesWithSubcategoriesView.as_view(), name='categories-with-subcategories'),
]