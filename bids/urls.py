from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BidViewSet, BidDocumentViewSet, BidFinancialResponseViewSet,
    BidTurnoverResponseViewSet, BidExperienceResponseViewSet,
    BidPersonnelResponseViewSet, BidOfficeResponseViewSet,
    BidSourceResponseViewSet, BidLitigationResponseViewSet,
    BidScheduleResponseViewSet, BidTechnicalResponseViewSet,
    BidEvaluationViewSet, BidAuditLogViewSet
)

app_name = 'bids'

router = DefaultRouter()
router.register(r'bids', BidViewSet, basename='bid')
router.register(r'bid-documents', BidDocumentViewSet, basename='bid-document')
router.register(r'bid-financial-responses', BidFinancialResponseViewSet, basename='bid-financial-response')
router.register(r'bid-turnover-responses', BidTurnoverResponseViewSet, basename='bid-turnover-response')
router.register(r'bid-experience-responses', BidExperienceResponseViewSet, basename='bid-experience-response')
router.register(r'bid-personnel-responses', BidPersonnelResponseViewSet, basename='bid-personnel-response')
router.register(r'bid-office-responses', BidOfficeResponseViewSet, basename='bid-office-response')
router.register(r'bid-source-responses', BidSourceResponseViewSet, basename='bid-source-response')
router.register(r'bid-litigation-responses', BidLitigationResponseViewSet, basename='bid-litigation-response')
router.register(r'bid-schedule-responses', BidScheduleResponseViewSet, basename='bid-schedule-response')
router.register(r'bid-technical-responses', BidTechnicalResponseViewSet, basename='bid-technical-response')
router.register(r'bid-evaluations', BidEvaluationViewSet, basename='bid-evaluation')
router.register(r'bid-audit-logs', BidAuditLogViewSet, basename='bid-audit-log')

urlpatterns = [
    path('', include(router.urls)),
]