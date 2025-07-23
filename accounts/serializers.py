import os
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from tenders.models import Tender
from bids.serializers import BidSerializer

from .models import (
    CustomUser, Company, CompanyUser, CompanyInvitation, CompanyDocument,
    CompanyOffice, CompanyCertification, CompanySourceOfFund,
    CompanyAnnualTurnover, CompanyFinancialStatement,
    CompanyLitigation, CompanyEquipment, CompanyPersonnel, AuditLog
)
from .constants import VALID_FILE_EXTENSIONS, MAX_FILE_SIZE, MAX_COMPANIES_PER_USER, MAX_COMPANY_USERS
from .permissions import IsCompanyAdminOrOwner


# ───── User & Profile ──────────────────────────────────────────────────────────

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'phone_number', 'first_name', 'last_name']
        read_only_fields = ['id', 'email']


class CustomUserCreateSerializer(serializers.ModelSerializer):
    invitation_token = serializers.CharField(required=False, write_only=True)
    phone_number = serializers.CharField(required=True, min_length=10, max_length=20)

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'phone_number', 'password',
            'first_name', 'last_name', 'invitation_token'
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_invitation_token(self, token):
        if token and not CompanyInvitation.objects.filter(
            token=token, accepted=False, expires_at__gt=timezone.now()
        ).exists():
            raise serializers.ValidationError("Invalid invitation token.")
        return token

    def create(self, validated_data):
        token = validated_data.pop('invitation_token', None)
        phone = validated_data.pop('phone_number')
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name',''),
            last_name=validated_data.get('last_name','')
        )
        user.phone_number = phone
        user.save(update_fields=['phone_number'])

        if token:
            inv = get_object_or_404(
                CompanyInvitation,
                token=token,
                invited_email=user.email,
                accepted=False,
                expires_at__gt=timezone.now(),
                company__deleted_at__isnull=True
            )
            company = inv.company
            if company.company_users.count() >= MAX_COMPANY_USERS:
                raise serializers.ValidationError("Company full.")
            CompanyUser.objects.create(company=company, user=user, role=inv.role)
            inv.accepted = True
            inv.save(update_fields=['accepted'])
        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'phone_number']


# ───── Core Company CRUD Serializers ───────────────────────────────────────────

class CompanySerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    slug = serializers.SlugField(read_only=True)
    owner_email = serializers.SerializerMethodField()
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        default=serializers.CurrentUserDefault(),
        write_only=True
    )

    class Meta:
        model = Company
        depth=1
        fields = (
            'id', 'name', 'slug', 'description', 'industry', 'website', 'logo',
            'tax_id', 'registration_number', 'founded_date', 'country',
            'key_activities', 'naics_code', 'status', 'is_verified',
            'verification_date', 'employee_count', 'parent_company',
            'owner', 'owner_email', 'deleted_at', 'created_at', 'updated_at',
            'created_by'
        )
        read_only_fields = ('deleted_at', 'created_at', 'updated_at')

    def get_owner_email(self, obj):
        return obj.owner.email

    def validate(self, attrs):
        user = self.context['request'].user
        if self.instance is None and Company.objects.filter(
            owner=user, deleted_at__isnull=True
        ).exists():
            raise serializers.ValidationError({
                'owner': f"A user can only own {MAX_COMPANIES_PER_USER} company."
            })
        return attrs

    def validate_name(self, value):
        if Company.objects.filter(
            name__iexact=value, deleted_at__isnull=True
        ).exists():
            raise serializers.ValidationError("Company name already exists.")
        return value


# ───── Tender Bid Nesting ─────────────────────────────────────────────────────

class TenderSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Tender
        fields = ['id', 'title', 'submission_deadline']


class CompanyBidSerializer(BidSerializer):
    tender = TenderSummarySerializer(read_only=True)

    class Meta(BidSerializer.Meta):
        fields = BidSerializer.Meta.fields + ['tender']


# ───── Flat “Member” Serializers ──────────────────────────────────────────────

class CompanyUserSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = CompanyUser
        fields = ['id', 'user', 'user_email', 'role']
        read_only_fields = ['id', 'user_email']


class CompanyInvitationSerializer(serializers.ModelSerializer):
    invited_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CompanyInvitation
        fields = ['id', 'invited_email', 'role', 'accepted', 'created_at', 'expires_at']
        read_only_fields = ['id', 'accepted', 'created_at']


class CompanyDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = CompanyDocument
        fields = ['id', 'document_type', 'document_category', 'document_file', 'uploaded_at', 'expires_at', 'status']
        read_only_fields = ['id', 'uploaded_at', 'status']

    def validate_document_file(self, file):
        if file.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(f"Max file size is {MAX_FILE_SIZE//(1024*1024)}MB")
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in VALID_FILE_EXTENSIONS:
            raise serializers.ValidationError("Unsupported format.")
        return file


# ───── Flat Office/Cert/etc ─────────────────────────────────────────────────

class CompanyOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyOffice
        fields = ['uuid', 'director_title', 'phone', 'email',
                  'physical_address', 'postal_address', 'region',
                  'district', 'council', 'ward', 'street']


class CompanyCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyCertification
        fields = ['id', 'cert_type', 'name', 'file', 'issued_date', 'expiry_date', 'notes']
        read_only_fields = ['id']


class CompanySourceOfFundSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySourceOfFund
        fields = ['id', 'source_type', 'amount', 'currency', 'proof']
        read_only_fields = ['id']


class CompanyAnnualTurnoverSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyAnnualTurnover
        fields = ['year', 'amount', 'currency']


class CompanyFinancialStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyFinancialStatement
        fields = ['year', 'currency', 'total_assets', 'total_liabilities',
                  'total_equity', 'gross_profit', 'profit_before_tax',
                  'cash_flow', 'file', 'audit_report', 'uploaded_at']
        read_only_fields = ['uploaded_at']


class CompanyLitigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyLitigation
        fields = ['id', 'title', 'description', 'start_date', 'end_date', 'status']
        read_only_fields = ['id']


class CompanyEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyEquipment
        fields = ['id', 'name', 'quantity', 'description']
        read_only_fields = ['id']


class CompanyPersonnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyPersonnel
        fields = ['id', 'name', 'role', 'education', 'years_experience', 'professional_registration']
        read_only_fields = ['id']


# ───── Deep‐Nesting for “/users/me” or Detail ─────────────────────────────────

class CompanyNestedSerializer(CompanySerializer):
    company_users        = CompanyUserSerializer(many=True,   read_only=True)
    invitations          = CompanyInvitationSerializer(many=True, read_only=True)
    documents            = CompanyDocumentSerializer(many=True,  read_only=True)
    offices              = CompanyOfficeSerializer(many=True,    read_only=True)
    certifications       = CompanyCertificationSerializer(many=True, read_only=True)
    sources_of_funds     = CompanySourceOfFundSerializer(many=True, read_only=True)
    annual_turnovers     = CompanyAnnualTurnoverSerializer(many=True, read_only=True)
    financial_statements = CompanyFinancialStatementSerializer(many=True, read_only=True)
    litigations          = CompanyLitigationSerializer(many=True,   read_only=True)
    equipment            = CompanyEquipmentSerializer(many=True,    read_only=True)
    personnel            = CompanyPersonnelSerializer(many=True,   read_only=True)
    bids                 = CompanyBidSerializer(many=True,          read_only=True, source='company_bids')

    class Meta(CompanySerializer.Meta):
        fields = CompanySerializer.Meta.fields + (
            'company_users','invitations','documents','offices',
            'certifications','sources_of_funds','annual_turnovers',
            'financial_statements','litigations','equipment',
            'personnel','bids'
        )


class CustomUserDetailSerializer(serializers.ModelSerializer):
    companies = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id','email','phone_number','first_name','last_name',
            'is_active','is_staff','is_superuser','companies'
        ]
        read_only_fields = fields

    def get_companies(self, obj):
        qs = Company.objects.filter(
            Q(owner=obj) | Q(company_users__user=obj),
            deleted_at__isnull=True
        ).distinct().select_related('owner')
        return CompanyNestedSerializer(qs, many=True, context=self.context).data


class AuditLogSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'user', 'timestamp', 'details']
        read_only_fields = fields
