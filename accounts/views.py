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
    CompanyEquipment,
    CompanyPersonnel,
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
    CompanyEquipmentSerializer,
    CompanyPersonnelSerializer,
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
        company = get_object_or_404(Company, id=self.kwargs['company_pk'], deleted_at__isnull=True)
        if CompanyUser.objects.filter(company=company).count() >= MAX_COMPANY_USERS:
            raise ValidationError(f"Max users per company ({MAX_COMPANY_USERS}) reached.")
        with transaction.atomic():
            cu = serializer.save(company=company)
            AuditLog.objects.create(
                action='company_user_added',
                user=self.request.user,
                details={'company_id': str(company.id), 'user_id': cu.user.id}
            )

    def perform_destroy(self, instance):
        if instance.role == 'owner':
            raise PermissionDenied("Cannot remove company owner.")
        with transaction.atomic():
            AuditLog.objects.create(
                action='company_user_removed',
                user=self.request.user,
                details={'company_id': str(instance.company.id), 'user_id': instance.user.id}
            )
            instance.delete()


class CompanyInvitationViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyInvitation; only company admins/owners.
    Sends email on create.
    """
    serializer_class = CompanyInvitationSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyInvitation.objects.filter(
            company_id=self.kwargs['company_pk'],
            expires_at__gt=timezone.now(),
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, id=self.kwargs['company_pk'], deleted_at__isnull=True)
        invited_email = serializer.validated_data.get('invited_email')
        if CompanyInvitation.objects.filter(
            company=company,
            invited_email=invited_email,
            expires_at__gt=timezone.now()
        ).exists():
            raise ValidationError("An active invitation for this email already exists.")
        with transaction.atomic():
            inv = serializer.save(company=company, invited_by=self.request.user)
            url = self.request.build_absolute_uri(
                reverse('accounts:company-invitations-detail', kwargs={
                    'company_pk': company.id,
                    'pk': inv.id
                })
            )
            send_mail(
                subject=f"You're invited to join {company.name}",
                message=f"Please accept your invitation: {url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invited_email]
            )
            AuditLog.objects.create(
                action='invitation_sent',
                user=self.request.user,
                details={'company_id': str(company.id), 'invited_email': invited_email}
            )


class CompanyDocumentViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyDocument; only company owners.
    Validates file extension and size.
    """
    serializer_class = CompanyDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwner]
    throttle_classes = [UserRateThrottle]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return CompanyDocument.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        file = serializer.validated_data.get('file')
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in VALID_FILE_EXTENSIONS:
            raise ValidationError("Unsupported file extension.")
        if file.size > MAX_FILE_SIZE:
            raise ValidationError("File too large.")
        with transaction.atomic():
            doc = serializer.save(
                company=get_object_or_404(
                    Company, id=self.kwargs['company_pk'], deleted_at__isnull=True
                ),
                uploaded_by=self.request.user
            )
            AuditLog.objects.create(
                action='document_uploaded',
                user=self.request.user,
                details={'company_id': str(doc.company.id), 'document_id': str(doc.id)}
            )


class CompanyOfficeViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyOffice; only company admins/owners.
    """
    serializer_class = CompanyOfficeSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyOffice.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        company = get_object_or_404(Company, id=self.kwargs['company_pk'], deleted_at__isnull=True)
        with transaction.atomic():
            office = serializer.save(company=company)
            AuditLog.objects.create(
                action='office_created',
                user=self.request.user,
                details={'company_id': str(company.id), 'office_uuid': str(office.uuid)}
            )

    def perform_destroy(self, instance):
        uuid = instance.uuid
        company_id = instance.company.id
        with transaction.atomic():
            instance.delete()
            AuditLog.objects.create(
                action='office_deleted',
                user=self.request.user,
                details={'company_id': str(company_id), 'office_uuid': str(uuid)}
            )


class CompanyCertificationViewSet(viewsets.ModelViewSet):
    """
    CRUD for CompanyCertification; only company admins/owners.
    Validates file extension and size.
    """
    serializer_class = CompanyCertificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return CompanyCertification.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        file = serializer.validated_data.get('file')
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in VALID_FILE_EXTENSIONS:
            raise ValidationError("Unsupported file extension.")
        if file.size > MAX_FILE_SIZE:
            raise ValidationError("File too large.")
        with transaction.atomic():
            cert = serializer.save(
                company=get_object_or_404(
                    Company, id=self.kwargs['company_pk'], deleted_at__isnull=True
                ) 
            )
            AuditLog.objects.create(
                action='certification_uploaded',
                user=self.request.user,
                details={'company_id': str(cert.company.id), 'cert_id': cert.id}               
            )


class CompanySourceOfFundViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySourceOfFundSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanySourceOfFund.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        src = serializer.save(
            company=get_object_or_404(
                Company, id=self.kwargs['company_pk'], deleted_at__isnull=True
            )
        )
        AuditLog.objects.create(
            action='source_of_fund_added',
            user=self.request.user,
            details={'company_id': str(src.company.id), 'source_id': src.id}
        )


class CompanyAnnualTurnoverViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyAnnualTurnoverSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]
    lookup_field = 'year'

    def get_queryset(self):
        return CompanyAnnualTurnover.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        turnover = serializer.save(
            company=get_object_or_404(Company, id=self.kwargs['company_pk'], deleted_at__isnull=True)
        )
        AuditLog.objects.create(
            action='annual_turnover_added',
            user=self.request.user,
            details={'company_id': str(turnover.company.id), 'year': turnover.year}
        )


class CompanyFinancialStatementViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyFinancialStatementSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'year'

    def get_queryset(self):
        return CompanyFinancialStatement.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        file = serializer.validated_data.get('file')
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in VALID_FILE_EXTENSIONS:
            raise ValidationError("Unsupported file extension.")
        if file.size > MAX_FILE_SIZE:
            raise ValidationError("File too large.")
        fs = serializer.save(
            company=get_object_or_404(Company, id=self.kwargs['company_pk'], deleted_at__isnull=True)
        )
        AuditLog.objects.create(
            action='financial_statement_uploaded',
            user=self.request.user,
            details={'company_id': str(fs.company.id), 'year': fs.year}
        )


class CompanyLitigationViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyLitigationSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyLitigation.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        lit = serializer.save(
            company=get_object_or_404(Company, id=self.kwargs['company_pk'], deleted_at__isnull=True)
        )
        AuditLog.objects.create(
            action='litigation_recorded',
            user=self.request.user,
            details={'company_id': str(lit.company.id), 'litigation_id': lit.id}
        )


class CompanyEquipmentViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyEquipmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyEquipment.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        eq = serializer.save(
            company=get_object_or_404(Company, id=self.kwargs['company_pk'], deleted_at__isnull=True)
        )
        AuditLog.objects.create(
            action='equipment_added',
            user=self.request.user,
            details={'company_id': str(eq.company.id), 'equipment_id': eq.id}
        )


class CompanyPersonnelViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyPersonnelSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyAdminOrOwner]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return CompanyPersonnel.objects.filter(
            company_id=self.kwargs['company_pk'],
            company__deleted_at__isnull=True
        )

    def perform_create(self, serializer):
        pers = serializer.save(
            company=get_object_or_404(Company, id=self.kwargs['company_pk'], deleted_at__isnull=True)
        )
        AuditLog.objects.create(
            action='personnel_added',
            user=self.request.user,
            details={'company_id': str(pers.company.id), 'personnel_id': pers.id}
        )


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only audit logs for admins.
    """
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = None  # set your AuditLogSerializer
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
