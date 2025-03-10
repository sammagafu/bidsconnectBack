# tenders/urls.py
from django.urls import path
from .views import (
    CategoryListCreateView, CategoryRetrieveUpdateDestroyView,
    SubCategoryListCreateView, SubCategoryRetrieveUpdateDestroyView,
    ProcurementProcessListCreateView, ProcurementProcessRetrieveUpdateDestroyView,
    TenderListCreateView, TenderRetrieveUpdateDestroyView,
    TenderDocumentListCreateView, TenderDocumentRetrieveUpdateDestroyView,
    TenderSubscriptionListCreateView, TenderSubscriptionRetrieveUpdateDestroyView,
    NotificationPreferenceRetrieveUpdateView, TenderNotificationListView,
    publish_tender
)

urlpatterns = [
    # Category URLs
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', CategoryRetrieveUpdateDestroyView.as_view(), name='category-detail'),

    # SubCategory URLs
    path('subcategories/', SubCategoryListCreateView.as_view(), name='subcategory-list-create'),
    path('subcategories/<int:pk>/', SubCategoryRetrieveUpdateDestroyView.as_view(), name='subcategory-detail'),

    # ProcurementProcess URLs
    path('procurement-processes/', ProcurementProcessListCreateView.as_view(), name='procurement-process-list-create'),
    path('procurement-processes/<int:pk>/', ProcurementProcessRetrieveUpdateDestroyView.as_view(), name='procurement-process-detail'),

    # Tender URLs
    path('tenders/', TenderListCreateView.as_view(), name='tender-list-create'),
    path('tenders/<int:pk>/', TenderRetrieveUpdateDestroyView.as_view(), name='tender-detail'),
    path('tenders/<int:pk>/publish/', publish_tender, name='tender-publish'),

    # TenderDocument URLs
    path('tender-documents/', TenderDocumentListCreateView.as_view(), name='tender-document-list-create'),
    path('tender-documents/<int:pk>/', TenderDocumentRetrieveUpdateDestroyView.as_view(), name='tender-document-detail'),

    # TenderSubscription URLs
    path('subscriptions/', TenderSubscriptionListCreateView.as_view(), name='subscription-list-create'),
    path('subscriptions/<int:pk>/', TenderSubscriptionRetrieveUpdateDestroyView.as_view(), name='subscription-detail'),

    # NotificationPreference URLs
    path('notification-preferences/', NotificationPreferenceRetrieveUpdateView.as_view(), name='notification-preference'),

    # TenderNotification URLs
    path('notifications/', TenderNotificationListView.as_view(), name='notification-list'),
]