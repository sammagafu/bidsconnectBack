# tenders/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    SubCategoryViewSet,
    CategoryWithSubcategoriesViewSet,
    ProcurementProcessViewSet,
    AgencyDetailsViewSet,
    TenderViewSet,
    TenderRequiredDocumentViewSet,
    TenderFinancialRequirementViewSet,
    TenderTurnoverRequirementViewSet,
    TenderExperienceRequirementViewSet,
    TenderPersonnelRequirementViewSet,
    TenderScheduleItemViewSet,
    TenderSubscriptionViewSet,
    NotificationPreferenceViewSet,
    TenderNotificationViewSet,
    TenderStatusHistoryViewSet,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'subcategories', SubCategoryViewSet, basename='subcategory')
router.register(r'categories-with-subcategories', CategoryWithSubcategoriesViewSet, basename='cat-with-subs')
router.register(r'procurement-processes', ProcurementProcessViewSet, basename='procurement')
router.register(r'agencies', AgencyDetailsViewSet, basename='agency')

router.register(r'tenders', TenderViewSet, basename='tender')
router.register(r'tender-documents', TenderRequiredDocumentViewSet, basename='tender-doc')
router.register(r'tender-financials', TenderFinancialRequirementViewSet, basename='tender-financial')
router.register(r'tender-turnovers', TenderTurnoverRequirementViewSet, basename='tender-turnover')
router.register(r'tender-experiences', TenderExperienceRequirementViewSet, basename='tender-experience')
router.register(r'tender-personnel', TenderPersonnelRequirementViewSet, basename='tender-personnel')
router.register(r'tender-schedule-items', TenderScheduleItemViewSet, basename='tender-schedule')

router.register(r'subscriptions', TenderSubscriptionViewSet, basename='subscription')
router.register(r'notification-preferences', NotificationPreferenceViewSet, basename='notify-pref')
router.register(r'tender-notifications', TenderNotificationViewSet, basename='tender-notif')
router.register(r'tender-status-history', TenderStatusHistoryViewSet, basename='tender-status')

urlpatterns = [
    path('', include(router.urls)),
]
