# bids/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BidViewSet, BidDocumentViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'bids', BidViewSet, basename='bid')
router.register(r'bid-documents', BidDocumentViewSet, basename='bid-document')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]
