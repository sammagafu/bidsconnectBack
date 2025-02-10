# views.py
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import Company, CompanyUser, CompanyInvitation, CompanyDocument
from .serializers import (
    CompanySerializer,
    CompanyUserSerializer,
    CompanyInvitationSerializer,
    UserProfileUpdateSerializer,
    CompanyDocumentSerializer,
    CustomUserCreateSerializer
)
from .permissions import IsCompanyOwner, IsCompanyAdminOrOwner, IsCompanyMember

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = CustomUserCreateSerializer
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'detail': 'User registered successfully'}, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )

class CompanyListView(generics.ListCreateAPIView):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.companies.all()

    def perform_create(self, serializer):
        with transaction.atomic():
            company = serializer.save(owner=self.request.user)
            # Additional setup for new company can be added here

class CompanyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsCompanyOwner]

    def get_object(self):
        company = super().get_object()
        if company.owner != self.request.user:
            raise PermissionDenied("You don't own this company")
        return company

class CompanyUserManagementView(generics.ListCreateAPIView):
    serializer_class = CompanyUserSerializer
    permission_classes = [IsCompanyAdminOrOwner]

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return CompanyUser.objects.filter(company_id=company_id)

    @transaction.atomic
    def perform_create(self, serializer):
        company = get_object_or_404(Company, id=self.kwargs['company_id'])
        if company.company_users.count() >= 5:
            raise ValidationError("Maximum of 5 users per company reached")
        
        serializer.save(company=company)
        
class CompanyUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CompanyUserSerializer
    permission_classes = [IsCompanyAdminOrOwner]
    queryset = CompanyUser.objects.all()

    def get_object(self):
        obj = super().get_object()
        if obj.role == 'owner':
            raise PermissionDenied("Cannot modify company owner")
        return obj

class InvitationListView(generics.ListAPIView):
    serializer_class = CompanyInvitationSerializer
    permission_classes = [IsCompanyAdminOrOwner]

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return CompanyInvitation.objects.filter(
            company_id=company_id, 
            expires_at__gt=timezone.now()
        )

class InvitationDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = CompanyInvitationSerializer
    permission_classes = [IsCompanyAdminOrOwner]
    queryset = CompanyInvitation.objects.all()

class DocumentManagementView(generics.ListCreateAPIView):
    serializer_class = CompanyDocumentSerializer
    permission_classes = [IsCompanyAdminOrOwner]

    def get_queryset(self):
        return CompanyDocument.objects.filter(
            company_id=self.kwargs['company_id']
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, id=self.kwargs['company_id'])
        serializer.save(company=company, uploaded_by=self.request.user)

class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CompanyDocumentSerializer
    permission_classes = [IsCompanyAdminOrOwner]
    queryset = CompanyDocument.objects.all()

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class InvitationAcceptanceView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, token):
        invitation = get_object_or_404(
            CompanyInvitation,
            token=token,
            invited_email=request.user.email,
            accepted=False,
            expires_at__gt=timezone.now()
        )
        
        if CompanyUser.objects.filter(company=invitation.company, user=request.user).exists():
            raise ValidationError("You already belong to this company")
        
        CompanyUser.objects.create(
            company=invitation.company,
            user=request.user,
            role=invitation.role
        )
        invitation.accepted = True
        invitation.save()
        
        return Response({"detail": "Invitation accepted successfully"})