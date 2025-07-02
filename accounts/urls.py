# accounts/urls.py

from django.urls import path
from .views import (
    UserRegistrationView,
    CompanyListView, CompanyDetailView,
    CompanyUserManagementView, CompanyUserDetailView,
    InvitationListView, InvitationDetailView, InvitationAcceptanceView,
    DocumentManagementView, DocumentDetailView,
    UserProfileView,
    OwnerCompanyListView, AdminCompanyListView,
    PublicInvitationAcceptanceView,  # ← imported here
)

urlpatterns = [
    path('auth/register/', UserRegistrationView.as_view(), name='user-register'),

    path('companies/', CompanyListView.as_view(), name='company-list'),
    path('companies/owner/', OwnerCompanyListView.as_view(), name='owner-company-list'),
    path('companies/admin/', AdminCompanyListView.as_view(), name='admin-company-list'),
    path('companies/<uuid:id>/', CompanyDetailView.as_view(), name='company-detail'),

    path('companies/<uuid:company_id>/users/', CompanyUserManagementView.as_view(), name='company-users'),
    path('companies/<uuid:company_id>/users/<int:id>/', CompanyUserDetailView.as_view(), name='company-user-detail'),

    path('companies/<uuid:company_id>/invitations/', InvitationListView.as_view(), name='invitation-list'),
    path('companies/<uuid:company_id>/invitations/<int:id>/', InvitationDetailView.as_view(), name='invitation-detail'),
    path('companies/<uuid:company_id>/accept-invitation/<str:token>/', InvitationAcceptanceView.as_view(), name='accept-invitation'),

    path('companies/<uuid:company_id>/documents/', DocumentManagementView.as_view(), name='document-list'),
    path('companies/<uuid:company_id>/documents/<int:id>/', DocumentDetailView.as_view(), name='document-detail'),

    path('profile/', UserProfileView.as_view(), name='user-profile'),

    # Public, token-only invitation accept (no company_id)
    path(
        'accept-invitation/<str:token>/',
        PublicInvitationAcceptanceView.as_view(),
        name='public-accept-invitation'
    ),
]
