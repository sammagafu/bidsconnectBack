from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    UserProfileViewSet,
    CompanyViewSet,
    CompanyUserViewSet,
    CompanyInvitationViewSet,
    CompanyDocumentViewSet,
    CompanyOfficeViewSet,
    CompanyCertificationViewSet,
    CompanyBiddingProfileViewSet,  # NEW: Import new ViewSet
    CompanySourceOfFundViewSet,
    CompanyAnnualTurnoverViewSet,
    CompanyFinancialStatementViewSet,
    CompanyLitigationViewSet,
    CompanyPersonnelViewSet,
    AuditLogViewSet,
    InvitationAcceptanceView,
    CompanyDocumentCSVExportView,
    DocumentExpiryWebhookView,
    CompanyDashboardView,
)

app_name = 'accounts'

router = DefaultRouter()
router.register(r'users', UserProfileViewSet, basename='user')
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

# Nested-style endpoints using regex prefixes without extra dependency
router.register(
    r'companies/(?P<company_pk>[^/.]+)/users',
    CompanyUserViewSet,
    basename='company-users'
)
router.register(
    r'companies/(?P<company_pk>[^/.]+)/invitations',
    CompanyInvitationViewSet,
    basename='company-invitations'
)
router.register(
    r'companies/(?P<company_pk>[^/.]+)/documents',
    CompanyDocumentViewSet,
    basename='company-documents'
)
router.register(
    r'companies/(?P<company_pk>[^/.]+)/offices',
    CompanyOfficeViewSet,
    basename='company-offices'
)
router.register(
    r'companies/(?P<company_pk>[^/.]+)/certifications',
    CompanyCertificationViewSet,
    basename='company-certifications'
)
# NEW: Nested for bidding profile
router.register(
    r'companies/(?P<company_pk>[^/.]+)/bidding-profile',
    CompanyBiddingProfileViewSet,
    basename='company-bidding-profile'
)
router.register(
    r'companies/(?P<company_pk>[^/.]+)/sources-of-fund',
    CompanySourceOfFundViewSet,
    basename='company-sources-of-fund'
)
router.register(
    r'companies/(?P<company_pk>[^/.]+)/annual-turnovers',
    CompanyAnnualTurnoverViewSet,
    basename='company-annual-turnovers'
)
router.register(
    r'companies/(?P<company_pk>[^/.]+)/financial-statements',
    CompanyFinancialStatementViewSet,
    basename='company-financial-statements'
)
router.register(
    r'companies/(?P<company_pk>[^/.]+)/litigations',
    CompanyLitigationViewSet,
    basename='company-litigations'
)

router.register(
    r'companies/(?P<company_pk>[^/.]+)/personnel',
    CompanyPersonnelViewSet,
    basename='company-personnel'
)

urlpatterns = router.urls + [
    # One-off endpoints
    path(
        'companies/<uuid:company_pk>/dashboard/',
        CompanyDashboardView.as_view(),
        name='company-dashboard'
    ),
    path(
        'companies/<uuid:company_pk>/documents/export/',
        CompanyDocumentCSVExportView.as_view(),
        name='company-documents-export'
    ),
    path(
        'invitations/accept/<str:token>/',
        InvitationAcceptanceView.as_view(),
        name='invitation-accept'
    ),
    path(
        'webhooks/documents/expiry/',
        DocumentExpiryWebhookView.as_view(),
        name='document-expiry-webhook'
    ),
]