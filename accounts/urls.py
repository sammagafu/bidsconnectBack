# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('companies/', views.CompanyListView.as_view(), name='company-list'),
    path('companies/<uuid:id>/', views.CompanyDetailView.as_view(), name='company-detail'),
    path('companies/<uuid:company_id>/users/', views.CompanyUserManagementView.as_view(), name='company-users'),
    path('companies/<uuid:company_id>/users/<int:id>/', views.CompanyUserDetailView.as_view(), name='company-user-detail'),
    path('companies/<uuid:company_id>/invitations/', views.InvitationListView.as_view(), name='invitation-list'),
    path('companies/<uuid:company_id>/invitations/<int:id>/', views.InvitationDetailView.as_view(), name='invitation-detail'),
    path('companies/<uuid:company_id>/documents/', views.DocumentManagementView.as_view(), name='document-list'),
    path('companies/<uuid:company_id>/documents/<int:id>/', views.DocumentDetailView.as_view(), name='document-detail'),
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('accept-invitation/<str:token>/', views.InvitationAcceptanceView.as_view(), name='accept-invitation'),
]