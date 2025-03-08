# accounts/urls.py
from django.urls import path
from .views import (
    UserRegistrationView,
    CompanyListView,
    CompanyDetailView,
    CompanyUserManagementView,
    InvitationListView,
    DocumentManagementView,
    InvitationAcceptanceView,
    UserProfileView,
    CompanyUserDetailView,
    InvitationDetailView,
    DocumentDetailView,
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('companies/', CompanyListView.as_view(), name='company-list'),
    path('companies/<uuid:id>/', CompanyDetailView.as_view(), name='company-detail'),
    path('companies/<uuid:company_id>/users/', CompanyUserManagementView.as_view(), name='company-users'),
    path('companies/<uuid:company_id>/users/<uuid:pk>/', CompanyUserDetailView.as_view(), name='company-user-detail'),
    path('companies/<uuid:company_id>/invitations/', InvitationListView.as_view(), name='invitation-list'),
    path('companies/<uuid:company_id>/invitations/<uuid:pk>/', InvitationDetailView.as_view(), name='invitation-detail'),
    path('companies/<uuid:company_id>/documents/', DocumentManagementView.as_view(), name='document-list'),
    path('companies/<uuid:company_id>/documents/<uuid:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('accept-invitation/<str:token>/', InvitationAcceptanceView.as_view(), name='accept-invitation'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]