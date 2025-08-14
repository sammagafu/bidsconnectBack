import logging
import os
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.urls import reverse

from rest_framework import viewsets, mixins, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .models import (
    CustomUser,
    Company,
    CompanyUser,
    CompanyInvitation,
    CompanyDocument,
    CompanyOffice,
    CompanyCertification,
    CompanySourceOfFund,
    CompanyAnnualTurnover,
    CompanyFinancialStatement,
    CompanyLitigation,
    CompanyPersonnel,
    CompanyExperience,
    AuditLog,
)
from .serializers import (
    CustomUserCreateSerializer,
    CustomUserDetailSerializer,
    UserProfileUpdateSerializer,
    CompanySerializer,
    CompanyUserSerializer,
    CompanyInvitationSerializer,
    CompanyDocumentSerializer,
    CompanyOfficeSerializer,
    CompanyCertificationSerializer,
    CompanySourceOfFundSerializer,
    CompanyAnnualTurnoverSerializer,
    CompanyFinancialStatementSerializer,
    CompanyLitigationSerializer,
    CompanyPersonnelSerializer,
    CompanyExperienceSerializer,
    AuditLogSerializer,
)
from .permissions import IsCompanyOwner, IsCompanyAdminOrOwner
from .constants import (
    MAX_COMPANY_USERS,
    MAX_COMPANIES_PER_USER,
    VALID_FILE_EXTENSIONS,
    MAX_FILE_SIZE,
)

logger = logging.getLogger(__name__)

class UserProfileViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    """
    Register, retrieve, and update user profiles.
    """
    queryset = CustomUser.objects.all()
    throttle_classes = [UserRateThrottle]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomUserCreateSerializer
        if self.action == 'retrieve':
            return CustomUserDetailSerializer
        return UserProfileUpdateSerializer

    def get_object(self):
        if self.action in ['retrieve', 'update', 'partial_update']:
            return self.request.user
        return super().get_object()

    def perform_create(self, serializer):
        with transaction.atomic():
            user = serializer.save()
            AuditLog.objects.create(
                action='user_registered',
                user=user,
                details={'user_id': str(user.id)}
            )

class CompanyViewSet(viewsets.ModelViewSet):
    """
    CRUD for Company; owners only, with soft-delete and company limits.
    """
    queryset = Company.objects.filter(deleted_at__isnull=True)
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def perform_create(self, serializer):
        if Company.objects.filter(owner=self.request.user, deleted_at__isnull=True).count() >= MAX_COMPANIES_PER_USER:
            raise ValidationError(f"Max companies per user ({MAX_COMPANIES_PER_USER}) reached.")
        with transaction.atomic():
            company = serializer.save(owner=self.request.user, created_by=self.request.user)
            AuditLog.objects.create(
                action='company_created',
                user=self.request.user,
                details={'company_id': str(company.id), 'name': company.name}
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.soft_delete()
            AuditLog.objects.create(
                action='company_deleted',
                user=self.request.user,
                details={'company_id': str(instance.id), 'name': instance.name}
            )

class CompanyUserViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyUser; only company admins/owners, with user limits.
    """
    serializer_class = CompanyUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyUser.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'], deleted_at__isnull=True)
        if company.accounts_company_users.count() >= MAX_COMPANY_USERS:
            raise ValidationError(f"Max users per company ({MAX_COMPANIES_PER_USER}) reached.")
        user = serializer.validated_data['user']
        with transaction.atomic():
            company_user = serializer.save(company=company)
            AuditLog.objects.create(
                action='user_added_to_company',
                user=self.request.user,
                details={
                    'company_id': str(company.id),
                    'user_id': str(user.id),
                    'role': company_user.role
                }
            )

class CompanyInvitationViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyInvitation; only company admins/owners, with email throttling.
    """
    serializer_class = CompanyInvitationSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyInvitation.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'], deleted_at__isnull=True)
        invited_email = serializer.validated_data['invited_email']
        if CompanyUser.objects.filter(company=company, user__email=invited_email).exists():
            raise ValidationError("User already in company.")
        with transaction.atomic():
            invitation = serializer.save(company=company, invited_by=self.request.user)
            accept_url = reverse('accounts:invitation-accept', kwargs={'token': invitation.token})
            send_mail(
                'Company Invitation',
                f'You are invited to join {company.name}. Accept: {settings.SITE_URL}{accept_url}',
                settings.DEFAULT_FROM_EMAIL,
                [invited_email],
                fail_silently=True
            )
            AuditLog.objects.create(
                action='invitation_sent',
                user=self.request.user,
                details={
                    'company_id': str(company.id),
                    'invited_email': invited_email
                }
            )

class CompanyDocumentViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyDocument; company members, with file validation and expiry notifications.
    """
    serializer_class = CompanyDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyDocument.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'], deleted_at__isnull=True)
        file = serializer.validated_data['file']
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in VALID_FILE_EXTENSIONS:
            raise ValidationError(f"Invalid file type: {ext}")
        if file.size > MAX_FILE_SIZE:
            raise ValidationError(f"File too large: {file.size} > {MAX_FILE_SIZE}")
        with transaction.atomic():
            document = serializer.save(company=company, uploaded_by=self.request.user)
            AuditLog.objects.create(
                action='document_uploaded',
                user=self.request.user,
                details={
                    'company_id': str(company.id),
                    'document_id': str(document.id),
                    'name': document.name
                }
            )

    def perform_update(self, serializer):
        instance = self.get_object()
        was_verified = instance.is_verified
        document = serializer.save()
        if not was_verified and document.is_verified:
            AuditLog.objects.create(
                action='document_verified',
                user=self.request.user,
                details={
                    'company_id': str(document.company.id),
                    'document_id': str(document.id)
                }
            )

class CompanyOfficeViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyOffice; company admins/owners only.
    """
    serializer_class = CompanyOfficeSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyOffice.objects.filter(
            company_id=self.kwargs['company_pk']
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'], deleted_at__isnull=True)
        serializer.save(company=company)

class CompanyCertificationViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyCertification; company admins/owners only.
    """
    serializer_class = CompanyCertificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyCertification.objects.filter(
            company_id=self.kwargs['company_pk']
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'], deleted_at__isnull=True)
        serializer.save(company=company)

class CompanySourceOfFundViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanySourceOfFund; company admins/owners only.
    """
    serializer_class = CompanySourceOfFundSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanySourceOfFund.objects.filter(
            company_id=self.kwargs['company_pk']
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'], deleted_at__isnull=True)
        with transaction.atomic():
            fund = serializer.save(company=company)
            AuditLog.objects.create(
                action='source_of_fund_added',
                user=self.request.user,
                details={
                    'company_id': str(fund.company.id),
                    'fund_id': str(fund.id),
                    'source_type': fund.source_type
                }
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            details = {
                'company_id': str(instance.company.id),
                'fund_id': str(instance.id),
                'source_type': instance.source_type
            }
            instance.delete()
            AuditLog.objects.create(
                action='source_of_fund_removed',
                user=self.request.user,
                details=details
            )

class CompanyAnnualTurnoverViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyAnnualTurnover; company admins/owners only.
    """
    serializer_class = CompanyAnnualTurnoverSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyAnnualTurnover.objects.filter(
            company_id=self.kwargs['company_pk']
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'], deleted_at__isnull=True)
        with transaction.atomic():
            turnover = serializer.save(company=company)
            AuditLog.objects.create(
                action='annual_turnover_added',
                user=self.request.user,
                details={
                    'company_id': str(turnover.company.id),
                    'turnover_id': str(turnover.id),
                    'year': turnover.year
                }
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            details = {
                'company_id': str(instance.company.id),
                'turnover_id': str(instance.id),
                'year': instance.year
            }
            instance.delete()
            AuditLog.objects.create(
                action='annual_turnover_removed',
                user=self.request.user,
                details=details
            )

class CompanyFinancialStatementViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyFinancialStatement; company admins/owners only.
    """
    serializer_class = CompanyFinancialStatementSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyFinancialStatement.objects.filter(
            company_id=self.kwargs['company_pk']
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'], deleted_at__isnull=True)
        with transaction.atomic():
            statement = serializer.save(company=company)
            AuditLog.objects.create(
                action='financial_statement_added',
                user=self.request.user,
                details={
                    'company_id': str(statement.company.id),
                    'statement_id': str(statement.id),
                    'year': statement.year
                }
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            details = {
                'company_id': str(instance.company.id),
                'statement_id': str(instance.id),
                'year': instance.year
            }
            instance.delete()
            AuditLog.objects.create(
                action='financial_statement_removed',
                user=self.request.user,
                details=details
            )

class CompanyLitigationViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyLitigation; company admins/owners only.
    """
    serializer_class = CompanyLitigationSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyLitigation.objects.filter(
            company_id=self.kwargs['company_pk']
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'], deleted_at__isnull=True)
        with transaction.atomic():
            litigation = serializer.save(company=company)
            AuditLog.objects.create(
                action='litigation_added',
                user=self.request.user,
                details={
                    'company_id': str(litigation.company.id),
                    'litigation_id': str(litigation.id),
                    'case_number': litigation.case_number
                }
            )

    def perform_update(self, serializer):
        instance = self.get_object()
        with transaction.atomic():
            litigation = serializer.save()
            AuditLog.objects.create(
                action='litigation_updated',
                user=self.request.user,
                details={
                    'company_id': str(litigation.company.id),
                    'litigation_id': str(litigation.id)
                }
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            details = {
                'company_id': str(instance.company.id),
                'litigation_id': str(instance.id),
                'case_number': instance.case_number
            }
            instance.delete()
            AuditLog.objects.create(
                action='litigation_removed',
                user=self.request.user,
                details=details
            )

class CompanyPersonnelViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyPersonnel; company admins/owners only.
    """
    serializer_class = CompanyPersonnelSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyPersonnel.objects.filter(
            company_id=self.kwargs['company_pk']
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'], deleted_at__isnull=True)
        with transaction.atomic():
            pers = serializer.save(company=company)
            AuditLog.objects.create(
                action='personnel_added',
                user=self.request.user,
                details={
                    'company_id': str(pers.company.id),
                    'personnel_uuid': str(pers.uuid),
                    'name': f"{pers.first_name} {pers.last_name}"
                }
            )

    def perform_update(self, serializer):
        instance = self.get_object()
        was_verified = instance.is_verified
        with transaction.atomic():
            pers = serializer.save()
            AuditLog.objects.create(
                action='personnel_updated',
                user=self.request.user,
                details={
                    'company_id': str(pers.company.id),
                    'personnel_uuid': str(pers.uuid),
                }
            )
            if not was_verified and pers.is_verified:
                AuditLog.objects.create(
                    action='personnel_verified',
                    user=self.request.user,
                    details={
                        'company_id': str(pers.company.id),
                        'personnel_uuid': str(pers.uuid),
                    }
                )

    def perform_destroy(self, instance):
        with transaction.atomic():
            details = {
                'company_id': str(instance.company.id),
                'personnel_uuid': str(instance.uuid),
                'name': f"{instance.first_name} {instance.last_name}"
            }
            instance.delete()
            AuditLog.objects.create(
                action='personnel_removed',
                user=self.request.user,
                details=details
            )

class CompanyExperienceViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyExperience; company admins/owners only.
    """
    serializer_class = CompanyExperienceSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyExperience.objects.filter(
            company_id=self.kwargs['company_pk']
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, pk=self.kwargs['company_pk'], deleted_at__isnull=True)
        with transaction.atomic():
            experience = serializer.save(company=company)
            AuditLog.objects.create(
                action='experience_added',
                user=self.request.user,
                details={
                    'company_id': str(experience.company.id),
                    'experience_id': str(experience.id),
                    'title': experience.title
                }
            )

    def perform_update(self, serializer):
        instance = self.get_object()
        with transaction.atomic():
            experience = serializer.save()
            AuditLog.objects.create(
                action='experience_updated',
                user=self.request.user,
                details={
                    'company_id': str(experience.company.id),
                    'experience_id': str(experience.id),
                    'title': experience.title
                }
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            details = {
                'company_id': str(instance.company.id),
                'experience_id': str(instance.id),
                'title': instance.title
            }
            instance.delete()
            AuditLog.objects.create(
                action='experience_removed',
                user=self.request.user,
                details=details
            )

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only audit logs for admins.
    """
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]

class CompanyDocumentCSVExportView(APIView):
    """
    GET /accounts/companies/{company_pk}/documents/export/ returns CSV export of documents.
    """
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner]

    def get(self, request, company_pk):
        # TODO: implement CSV generation
        return Response({"detail": "CSV export not implemented."},
                        status=status.HTTP_501_NOT_IMPLEMENTED)

class DocumentExpiryWebhookView(APIView):
    """
    POST /accounts/webhooks/documents/expiry/ handles document expiry webhooks.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # TODO: process webhook
        return Response({"detail": "Webhook received."}, status=status.HTTP_200_OK)

class CompanyDashboardView(APIView):
    """
    GET /accounts/companies/{company_pk}/dashboard/ returns company summary.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, company_pk):
        data = {
            "company_id": company_pk,
            "total_users": CompanyUser.objects.filter(company_id=company_pk).count(),
            "total_documents": CompanyDocument.objects.filter(company_id=company_pk).count(),
            "total_experiences": CompanyExperience.objects.filter(company_id=company_pk).count(),
        }
        return Response(data)

class InvitationAcceptanceView(APIView):
    """
    POST /accounts/invitations/accept/{token}/ endpoint to accept invitations.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        invitation = get_object_or_404(
            CompanyInvitation,
            token=token,
            expires_at__gt=timezone.now(),
            accepted=False
        )
        with transaction.atomic():
            CompanyUser.objects.create(
                company=invitation.company,
                user=request.user,
                role=invitation.role
            )
            invitation.accepted = True
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=['accepted', 'accepted_at'])
            AuditLog.objects.create(
                action='invitation_accepted',
                user=request.user,
                details={
                    'company_id': str(invitation.company.id),
                    'invitation_id': str(invitation.id)
                }
            )
        return Response(
            {"detail": f"Successfully joined {invitation.company.name}."},
            status=status.HTTP_200_OK
        )