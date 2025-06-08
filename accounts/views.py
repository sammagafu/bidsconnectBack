from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.throttling import UserRateThrottle
from .models import Company, CompanyUser, CompanyInvitation, CompanyDocument, AuditLog
from .serializers import (
    CompanySerializer,
    CompanyUserSerializer,
    CompanyInvitationSerializer,
    UserProfileUpdateSerializer,
    CompanyDocumentSerializer,
    CustomUserCreateSerializer
)
from .permissions import IsCompanyOwner, IsCompanyAdminOrOwner, IsCompanyMember

class CompanyListView(generics.ListCreateAPIView):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return Company.objects.filter(owner=self.request.user, deleted_at__isnull=True).select_related('owner')

    @transaction.atomic
    def perform_create(self, serializer):
        company = serializer.save(owner=self.request.user, created_by=self.request.user)
        AuditLog.objects.create(
            action='company_creation',
            user=self.request.user,
            details={'company_id': str(company.id), 'name': company.name}
        )

class CompanyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Company.objects.filter(deleted_at__isnull=True)
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    throttle_classes = [UserRateThrottle]

    def perform_destroy(self, instance):
        instance.soft_delete()
        AuditLog.objects.create(
            action='company_deletion',
            user=self.request.user,
            details={'company_id': str(instance.id), 'name': instance.name}
        )

class CompanyUserManagementView(generics.ListCreateAPIView):
    serializer_class = CompanyUserSerializer
    permission_classes = [IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return CompanyUser.objects.filter(company_id=company_id, company__deleted_at__isnull=True).select_related('user', 'company')

    @transaction.atomic
    def perform_create(self, serializer):
        company = get_object_or_404(Company, id=self.kwargs['company_id'], deleted_at__isnull=True)
        user = serializer.validated_data.get('user')
        
        if CompanyUser.objects.filter(company=company, user=user).exists():
            raise ValidationError({"user": "User already exists in this company"})
        
        company_user = serializer.save(company=company)
        AuditLog.objects.create(
            action='company_user_added',
            user=self.request.user,
            details={'company_id': str(company.id), 'user_id': user.id}
        )

class CompanyUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CompanyUserSerializer
    permission_classes = [IsCompanyAdminOrOwner]
    queryset = CompanyUser.objects.filter(company__deleted_at__isnull=True)
    lookup_field = 'id'
    throttle_classes = [UserRateThrottle]

    def get_object(self):
        obj = super().get_object()
        if obj.role == 'owner':
            raise PermissionDenied({"detail": "Cannot modify company owner"})
        return obj

class InvitationListView(generics.ListCreateAPIView):
    serializer_class = CompanyInvitationSerializer
    permission_classes = [IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return CompanyInvitation.objects.filter(
            company_id=company_id,
            company__deleted_at__isnull=True,
            expires_at__gt=timezone.now()
        ).select_related('company', 'invited_by')

    @transaction.atomic
    def perform_create(self, serializer):
        invitation = serializer.save(invited_by=self.request.user)
        
        send_mail(
            subject="Company Invitation",
            message=f"You have been invited to join {invitation.company.name}. Accept here: {settings.SITE_URL}/accept-invitation/{invitation.token}/",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitation.invited_email],
            fail_silently=False,
        )
        
        AuditLog.objects.create(
            action='invitation_sent',
            user=self.request.user,
            details={'company_id': str(invitation.company.id), 'invited_email': invitation.invited_email}
        )

class InvitationDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = CompanyInvitationSerializer
    permission_classes = [IsCompanyAdminOrOwner]
    queryset = CompanyInvitation.objects.filter(company__deleted_at__isnull=True)
    lookup_field = 'id'
    throttle_classes = [UserRateThrottle]

class DocumentManagementView(generics.ListCreateAPIView):
    serializer_class = CompanyDocumentSerializer
    permission_classes = [IsCompanyOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return CompanyDocument.objects.filter(
            company_id=company_id,
            company__deleted_at__isnull=True
        ).select_related('company', 'uploaded_by')

    @transaction.atomic
    def perform_create(self, serializer):
        company = get_object_or_404(Company, id=self.kwargs['company_id'], deleted_at__isnull=True)
        if company.owner != self.request.user:
            raise PermissionDenied({"detail": "Only company owner can upload documents"})
        
        document = serializer.save(company=company, uploaded_by=self.request.user)
        AuditLog.objects.create(
            action='document_uploaded',
            user=self.request.user,
            details={'company_id': str(company.id), 'document_id': str(document.id)}
        )

class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CompanyDocumentSerializer
    permission_classes = [IsCompanyOwner]
    queryset = CompanyDocument.objects.filter(company__deleted_at__isnull=True)
    lookup_field = 'id'
    throttle_classes = [UserRateThrottle]

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_object(self):
        return self.request.user

class InvitationAcceptanceView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    @transaction.atomic
    def post(self, request, token):
        invitation = get_object_or_404(
            CompanyInvitation,
            token=token,
            invited_email=request.user.email,
            accepted=False,
            expires_at__gt=timezone.now(),
            company__deleted_at__isnull=True
        )
        
        if CompanyUser.objects.filter(company=invitation.company, user=request.user).exists():
            raise ValidationError({"detail": "You already belong to this company"})
        
        if invitation.role == 'owner' and invitation.company.company_users.filter(role='owner').exists():
            raise ValidationError({"role": "Company already has an owner"})
        
        company_user = CompanyUser.objects.create(
            company=invitation.company,
            user=request.user,
            role=invitation.role
        )
        invitation.accepted = True
        invitation.save()
        
        AuditLog.objects.create(
            action='invitation_accepted',
            user=request.user,
            details={'company_id': str(invitation.company.id), 'role': invitation.role}
        )
        
        return Response({"detail": "Invitation accepted successfully"})

# New view for owners to list their companies
class OwnerCompanyListView(generics.ListAPIView):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        """Returns companies owned by the authenticated user, excluding soft-deleted ones."""
        return Company.objects.filter(owner=self.request.user, deleted_at__isnull=True).select_related('owner')

# New view for admins to list all companies
class AdminCompanyListView(generics.ListAPIView):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        """Returns all companies, including soft-deleted ones, for admin users."""
        return Company.objects.all().select_related('owner')