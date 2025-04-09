# tenders/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryListCreateView, CategoryRetrieveUpdateDestroyView,
    SubCategoryListCreateView, SubCategoryRetrieveUpdateDestroyView,
    ProcurementProcessListCreateView, ProcurementProcessRetrieveUpdateDestroyView,
    TenderListCreateView, TenderRetrieveUpdateDestroyView,
    TenderDocumentListCreateView, TenderDocumentRetrieveUpdateDestroyView,
    TenderSubscriptionViewSet,
    NotificationPreferenceRetrieveUpdateView, TenderNotificationListView,
    publish_tender,
    CategoryWithSubcategoriesCreateView
)

router = DefaultRouter()
router.register(r'subscriptions', TenderSubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<slug:slug>/', CategoryRetrieveUpdateDestroyView.as_view(), name='category-detail'),
    path('subcategories/', SubCategoryListCreateView.as_view(), name='subcategory-list-create'),
    path('subcategories/<slug:slug>/', SubCategoryRetrieveUpdateDestroyView.as_view(), name='subcategory-detail'),
    path('procurement-processes/', ProcurementProcessListCreateView.as_view(), name='procurement-process-list-create'),
    path('procurement-processes/<slug:slug>/', ProcurementProcessRetrieveUpdateDestroyView.as_view(), name='procurement-process-detail'),
    path('tenders/', TenderListCreateView.as_view(), name='tender-list-create'),
    path('tenders/<slug:slug>/', TenderRetrieveUpdateDestroyView.as_view(), name='tender-detail'),
    path('tenders/<slug:slug>/publish/', publish_tender, name='tender-publish'),
    path('tender-documents/', TenderDocumentListCreateView.as_view(), name='tender-document-list-create'),
    path('tender-documents/<int:pk>/', TenderDocumentRetrieveUpdateDestroyView.as_view(), name='tender-document-detail'),
    path('notification-preferences/', NotificationPreferenceRetrieveUpdateView.as_view(), name='notification-preference'),
    path('notifications/', TenderNotificationListView.as_view(), name='notification-list'),
    path('categories-with-subcategories/', CategoryWithSubcategoriesCreateView.as_view(), name='category-with-subcategories-create'),
] + router.urls