# accounts/views.py

import logging
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.urls import reverse

from rest_framework import generics, permissions, serializers
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.throttling import UserRateThrottle

from .models import (
    CustomUser, Company, CompanyUser,
    CompanyInvitation, CompanyDocument, AuditLog
)
from .serializers import (
    CustomUserCreateSerializer, CompanySerializer,
    CompanyUserSerializer, CompanyInvitationSerializer,
    CompanyDocumentSerializer, UserProfileUpdateSerializer
)
from .permissions import (
    IsCompanyOwner, IsCompanyAdminOrOwner, IsCompanyMember
)

logger = logging.getLogger(__name__)


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = CustomUserCreateSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [UserRateThrottle]


class CompanyListView(generics.ListCreateAPIView):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return Company.objects.filter(
            owner=self.request.user, deleted_at__isnull=True
        ).select_related('owner')

    @transaction.atomic
    def perform_create(self, serializer):
        comp = serializer.save(
            owner=self.request.user,
            created_by=self.request.user
        )
        AuditLog.objects.create(
            action='company_creation',
            user=self.request.user,
            details={'company_id': str(comp.id), 'name': comp.name}
        )


class CompanyDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CompanySerializer
    permission_classes = [IsCompanyOwner]
    throttle_classes = [UserRateThrottle]
    lookup_field = 'id'
    queryset = Company.objects.filter(deleted_at__isnull=True).select_related('owner')

    @transaction.atomic
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
        return CompanyUser.objects.filter(
            company_id=self.kwargs['company_id'],
            company__deleted_at__isnull=True
        ).select_related('user', 'company')

    @transaction.atomic
    def perform_create(self, serializer):
        company = get_object_or_404(
            Company, id=self.kwargs['company_id'], deleted_at__isnull=True
        )
        user = serializer.validated_data['user']
        if CompanyUser.objects.filter(company=company, user=user).exists():
            raise ValidationError({"user": "Already in this company"})
        cu = serializer.save(company=company)
        AuditLog.objects.create(
            action='company_user_added',
            user=self.request.user,
            details={'company_id': str(company.id), 'user_id': user.id}
        )


class CompanyUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CompanyUserSerializer
    permission_classes = [IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]
    lookup_field = 'id'
    queryset = CompanyUser.objects.filter(company__deleted_at__isnull=True)

    def get_object(self):
        obj = super().get_object()
        if obj.role == 'owner':
            raise PermissionDenied("Cannot modify owner")
        return obj


class InvitationListView(generics.ListCreateAPIView):
    serializer_class = CompanyInvitationSerializer
    permission_classes = [IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyInvitation.objects.filter(
            company_id=self.kwargs['company_id'],
            company__deleted_at__isnull=True,
            expires_at__gt=timezone.now()
        ).select_related('company', 'invited_by')

    @transaction.atomic
    def perform_create(self, serializer):
        inv = serializer.save(invited_by=self.request.user)

        # Build the correct accept-URL to our API endpoint
        accept_path = reverse(
            'accept-invitation',
            args=[inv.company.id, inv.token]
        )
        accept_url = f"{settings.SITE_URL.rstrip('/')}{accept_path}"

        try:
            send_mail(
                subject="Company Invitation",
                message=(
                    f"You've been invited to join {inv.company.name}.\n\n"
                    f"Accept here: {accept_url}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[inv.invited_email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"[InvitationListView] failed to send mail for invitation {inv.id}: {e}")

        AuditLog.objects.create(
            action='invitation_sent',
            user=self.request.user,
            details={'company_id': str(inv.company.id), 'invited_email': inv.invited_email}
        )


class InvitationDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = CompanyInvitationSerializer
    permission_classes = [IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]
    lookup_field = 'id'
    queryset = CompanyInvitation.objects.filter(company__deleted_at__isnull=True)


class InvitationAcceptanceView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    serializer_class = serializers.Serializer  # no input body expected

    @transaction.atomic
    def post(self, request, token):
        inv = get_object_or_404(
            CompanyInvitation,
            token=token,
            invited_email=request.user.email,
            accepted=False,
            expires_at__gt=timezone.now(),
            company__deleted_at__isnull=True
        )
        if CompanyUser.objects.filter(company=inv.company, user=request.user).exists():
            raise ValidationError("Already in this company")
        if inv.role == 'owner' and inv.company.company_users.filter(role='owner').exists():
            raise ValidationError("Owner already exists")

        CompanyUser.objects.create(company=inv.company, user=request.user, role=inv.role)
        inv.accepted = True
        inv.save(update_fields=['accepted'])
        AuditLog.objects.create(
            action='invitation_accepted',
            user=request.user,
            details={'company_id': str(inv.company.id), 'role': inv.role}
        )
        return Response({"detail": "Invitation accepted"})


class DocumentManagementView(generics.ListCreateAPIView):
    serializer_class = CompanyDocumentSerializer
    permission_classes = [IsCompanyOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyDocument.objects.filter(
            company_id=self.kwargs['company_id'],
            company__deleted_at__isnull=True
        ).select_related('company', 'uploaded_by')

    @transaction.atomic
    def perform_create(self, serializer):
        company = get_object_or_404(
            Company, id=self.kwargs['company_id'], deleted_at__isnull=True
        )
        if company.owner != self.request.user:
            raise PermissionDenied("Only owner can upload")
        doc = serializer.save(company=company, uploaded_by=self.request.user)
        AuditLog.objects.create(
            action='document_uploaded',
            user=self.request.user,
            details={'company_id': str(company.id), 'document_id': str(doc.id)}
        )


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CompanyDocumentSerializer
    permission_classes = [IsCompanyOwner]
    throttle_classes = [UserRateThrottle]
    lookup_field = 'id'
    queryset = CompanyDocument.objects.filter(company__deleted_at__isnull=True)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_object(self):
        return self.request.user


class OwnerCompanyListView(generics.ListAPIView):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return Company.objects.filter(owner=self.request.user, deleted_at__isnull=True)


class AdminCompanyListView(generics.ListAPIView):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return Company.objects.all().select_related('owner')


class PublicInvitationAcceptanceView(generics.GenericAPIView):
    """
    Public endpoint to accept an invitation by token alone.
    """
    serializer_class = serializers.Serializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [UserRateThrottle]

    def get(self, request, token):
        return Response(
            {"detail": "Use POST to accept this invitation."},
            status=405
        )

    @transaction.atomic
    def post(self, request, token):
        inv = get_object_or_404(
            CompanyInvitation,
            token=token,
            accepted=False,
            expires_at__gt=timezone.now(),
            company__deleted_at__isnull=True
        )

        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=401)
        if inv.invited_email.lower() != request.user.email.lower():
            return Response({"detail": "This invitation is not for your account."}, status=403)
        if CompanyUser.objects.filter(company=inv.company, user=request.user).exists():
            return Response({"detail": "Already a member."}, status=400)

        CompanyUser.objects.create(company=inv.company, user=request.user, role=inv.role)
        inv.accepted = True
        inv.save(update_fields=['accepted'])
        AuditLog.objects.create(
            action='invitation_accepted',
            user=request.user,
            details={'company_id': str(inv.company.id), 'role': inv.role}
        )
        return Response({"detail": f"Successfully joined {inv.company.name}."}, status=200)
