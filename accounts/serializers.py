# accounts/serializers.py

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
    CompanyOffice, CompanyCertification, CompanyBiddingProfile,  # NEW: Import new model
    CompanySourceOfFund,
    CompanyAnnualTurnover, CompanyFinancialStatement,
    CompanyLitigation, CompanyPersonnel, AuditLog
)
from .constants import VALID_FILE_EXTENSIONS, MAX_FILE_SIZE, MAX_COMPANIES_PER_USER, MAX_COMPANY_USERS


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
        fields = ['id', 'invited_email', 'role', 'accepted', 'created_at', 'expires_at', 'invited_by']
        read_only_fields = ['id', 'accepted', 'created_at', 'invited_by']


class CompanyDocumentSerializer(serializers.ModelSerializer):
    # We'll still use HiddenField to stamp the current user, 
    # but also include it in fields so DRF doesn’t complain
    uploaded_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = CompanyDocument
        fields = [
            'id',
            'uploaded_by',
            'document_type',
            'document_category',
            'document_file',
            'uploaded_at',
            'expires_at',
            'status',
        ]
        read_only_fields = ['id', 'uploaded_at', 'status', 'uploaded_by']

    def validate_document_file(self, file):
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in VALID_FILE_EXTENSIONS:
            raise serializers.ValidationError("Unsupported file extension.")
        if file.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(f"Max file size is {MAX_FILE_SIZE//(1024*1024)}MB")
        return file

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
    # Expose calculated ratios as read-only fields
    current_ratio = serializers.SerializerMethodField()
    cash_ratio = serializers.SerializerMethodField()
    working_capital = serializers.SerializerMethodField()
    gross_profit_margin = serializers.SerializerMethodField()
    debt_to_equity_ratio = serializers.SerializerMethodField()
    return_on_assets = serializers.SerializerMethodField()

    class Meta:
        model = CompanyFinancialStatement
        fields = [
            'year', 'currency', 'total_assets', 'total_liabilities',
            'total_equity', 'gross_profit', 'profit_before_tax',
            'cash_flow', 'file', 'audit_report', 'uploaded_at',
            'current_assets', 'current_liabilities', 'cash_and_bank', 'total_revenue',
            'current_ratio', 'cash_ratio', 'working_capital',
            'gross_profit_margin', 'debt_to_equity_ratio', 'return_on_assets'
        ]
        read_only_fields = ['uploaded_at', 'current_ratio', 'cash_ratio', 'working_capital',
                            'gross_profit_margin', 'debt_to_equity_ratio', 'return_on_assets']

    def get_current_ratio(self, obj):
        return obj.current_ratio

    def get_cash_ratio(self, obj):
        return obj.cash_ratio

    def get_working_capital(self, obj):
        return obj.working_capital

    def get_gross_profit_margin(self, obj):
        return obj.gross_profit_margin

    def get_debt_to_equity_ratio(self, obj):
        return obj.debt_to_equity_ratio

    def get_return_on_assets(self, obj):
        return obj.return_on_assets


class CompanyLitigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyLitigation
        fields = ['id', 'title', 'description', 'start_date', 'end_date', 'status']
        read_only_fields = ['id']


class CompanyPersonnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyPersonnel
        fields = [
            'id', 'uuid',
            'first_name', 'middle_name', 'last_name',
            'gender', 'date_of_birth', 'phone_number', 'email', 'physical_address',
            'employee_type', 'job_title', 'date_of_employment', 'language_spoken',
            'education', 'years_experience', 'professional_registration',
            'is_verified', 'verified_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'uuid', 'verified_at', 'created_at', 'updated_at']


# NEW: Serializer for CompanyBiddingProfile (moved after dependencies)
class CompanyBiddingProfileSerializer(serializers.ModelSerializer):
    sources_of_funds = CompanySourceOfFundSerializer(many=True, read_only=True)
    annual_turnovers = CompanyAnnualTurnoverSerializer(many=True, read_only=True)
    financial_statements = CompanyFinancialStatementSerializer(many=True, read_only=True)
    litigations = CompanyLitigationSerializer(many=True, read_only=True)
    personnel = CompanyPersonnelSerializer(many=True, read_only=True)

    class Meta:
        model = CompanyBiddingProfile
        fields = ['id', 'created_at', 'updated_at', 'sources_of_funds', 'annual_turnovers', 'financial_statements', 'litigations', 'personnel']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TenderSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Tender
        fields = ['id', 'title', 'submission_deadline']


class CompanyBidSerializer(BidSerializer):
    tender = TenderSummarySerializer(read_only=True)
    class Meta(BidSerializer.Meta):
        fields = BidSerializer.Meta.fields + ['tender']


class CompanySerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    slug = serializers.SlugField(read_only=True)
    owner_email = serializers.SerializerMethodField()

    # nested related data, all read-only:
    company_users        = CompanyUserSerializer(many=True,   read_only=True)
    invitations          = CompanyInvitationSerializer(many=True, read_only=True)
    documents            = CompanyDocumentSerializer(many=True,  read_only=True)
    offices              = CompanyOfficeSerializer(many=True,    read_only=True)
    certifications       = CompanyCertificationSerializer(many=True, read_only=True)
    bidding_profile      = CompanyBiddingProfileSerializer(read_only=True)  # NEW: Nest bidding profile
    bids                 = CompanyBidSerializer(many=True,          read_only=True, source='company_bids')

    class Meta:
        model = Company
        depth = 1
        fields = (
            'id','name','slug','description','industry','website','logo',
            'tax_id','registration_number','founded_date','country',
            'key_activities','naics_code','status','is_verified',
            'verification_date','employee_count','parent_company',
            'owner','owner_email','deleted_at','created_at','updated_at','created_by',

            # include all nested relations:
            'company_users','invitations','documents','offices',
            'certifications','bidding_profile','bids',  # UPDATED: Removed direct bidding nests, added bidding_profile
        )
        read_only_fields = (
            'deleted_at','created_at','updated_at',
            'company_users','invitations','documents','offices',
            'certifications','bidding_profile','bids',  # UPDATED
        )

    def get_owner_email(self, obj):
        return obj.owner.email

    def validate(self, attrs):
        user = self.context['request'].user
        if self.instance is None and Company.objects.filter(
            owner=user, deleted_at__isnull=True
        ).count() >= MAX_COMPANIES_PER_USER:
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
        return CompanySerializer(qs, many=True, context=self.context).data


class AuditLogSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'user', 'timestamp', 'details']
        read_only_fields = fields