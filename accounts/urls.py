# urls.py
from django.urls import path
from .views import (
    UserRegistrationView,
    CompanyListView,
    CompanyDetailView,
    CompanyUserManagementView,
    InvitationListView,
    DocumentManagementView,
    InvitationAcceptanceView,
    UserProfileView
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('companies/', CompanyListView.as_view(), name='company-list'),
    path('companies/<int:pk>/', CompanyDetailView.as_view(), name='company-detail'),
    path('companies/<int:company_id>/users/', CompanyUserManagementView.as_view(), name='company-users'),
    path('companies/<int:company_id>/invitations/', InvitationListView.as_view(), name='invitation-list'),
    path('companies/<int:company_id>/documents/', DocumentManagementView.as_view(), name='document-list'),
    path('accept-invitation/<str:token>/', InvitationAcceptanceView.as_view(), name='accept-invitation'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]