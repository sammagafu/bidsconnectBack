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
router.register(
    r'categories-with-subcategories',
    CategoryWithSubcategoriesViewSet,
    basename='cat-with-subs'
)
router.register(
    r'procurement-processes',
    ProcurementProcessViewSet,
    basename='procurement'
)
router.register(r'agencies', AgencyDetailsViewSet, basename='agency')

# this will give you:
#  /api/v1/tenders/            → list/create
#  /api/v1/tenders/{slug}/     → retrieve/update/delete
#  /api/v1/tenders/{slug}/publish/   → your custom action
#  /api/v1/tenders/{slug}/status/    → your custom action
#  /api/v1/tenders/{slug}/required-documents/ (GET, POST)
#  /api/v1/tenders/{slug}/financial-requirements/
#  /api/v1/tenders/{slug}/turnover-requirements/
#  /api/v1/tenders/{slug}/experience-requirements/
#  /api/v1/tenders/{slug}/personnel-requirements/
#  /api/v1/tenders/{slug}/schedule-items/
router.register(r'tenders', TenderViewSet, basename='tender')

# flat CRUD on each child (if you ever need it directly)
router.register(
    r'tender-documents',
    TenderRequiredDocumentViewSet,
    basename='tender-doc'
)
router.register(
    r'tender-financials',
    TenderFinancialRequirementViewSet,
    basename='tender-financial'
)
router.register(
    r'tender-turnovers',
    TenderTurnoverRequirementViewSet,
    basename='tender-turnover'
)
router.register(
    r'tender-experiences',
    TenderExperienceRequirementViewSet,
    basename='tender-experience'
)
router.register(
    r'tender-personnel',
    TenderPersonnelRequirementViewSet,
    basename='tender-personnel'
)
router.register(
    r'tender-schedule-items',
    TenderScheduleItemViewSet,
    basename='tender-schedule'
)

# subscriptions & notifications
router.register(
    r'subscriptions',
    TenderSubscriptionViewSet,
    basename='subscription'
)
router.register(
    r'notification-preferences',
    NotificationPreferenceViewSet,
    basename='notify-pref'
)
router.register(
    r'tender-notifications',
    TenderNotificationViewSet,
    basename='tender-notif'
)
router.register(
    r'tender-status-history',
    TenderStatusHistoryViewSet,
    basename='tender-status'
)

urlpatterns = [
    path('', include(router.urls)),
]
