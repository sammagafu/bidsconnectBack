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
    CompanyAnnualTurnover, CompanyFinancialStatement, CompanyLitigation,
    CompanyPersonnel, CompanyExperience, AuditLog
)
from .constants import (
    VALID_FILE_EXTENSIONS, MAX_FILE_SIZE, MAX_COMPANIES_PER_USER, MAX_COMPANY_USERS
)

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
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
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
            if company.accounts_company_users.count() >= MAX_COMPANY_USERS:
                raise serializers.ValidationError("Company user limit reached.")
            CompanyUser.objects.create(company=company, user=user, role=inv.role)
            inv.accepted = True
            inv.accepted_at = timezone.now()
            inv.save(update_fields=['accepted', 'accepted_at'])
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
        read_only_fields = ['id', 'accepted', 'created_at', 'expires_at', 'invited_by']

class CompanyDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = CompanyDocument
        fields = [
            'id', 'uploaded_by', 'name', 'document_type', 'category', 'file',
            'expiry_date', 'is_verified', 'uploaded_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uploaded_at', 'updated_at']

    def validate_file(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in VALID_FILE_EXTENSIONS:
            raise serializers.ValidationError(f"Invalid file type: {ext}")
        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(f"File too large: {value.size} > {MAX_FILE_SIZE}")
        return value

class CompanyOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyOffice
        fields = [
            'id', 'name', 'address', 'city', 'country', 'postal_code',
            'phone_number', 'is_headquarters', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class CompanyCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyCertification
        fields = [
            'id', 'name', 'issuing_authority', 'issue_date', 'expiry_date',
            'certificate_number', 'file', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class CompanySourceOfFundSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySourceOfFund
        fields = ['id', 'source_type', 'amount', 'currency', 'proof', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

class CompanyAnnualTurnoverSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyAnnualTurnover
        fields = ['id', 'year', 'amount', 'currency', 'proof', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

class CompanyFinancialStatementSerializer(serializers.ModelSerializer):
    current_ratio = serializers.ReadOnlyField()
    cash_ratio = serializers.ReadOnlyField()
    working_capital = serializers.ReadOnlyField()
    gross_profit_margin = serializers.ReadOnlyField()
    debt_to_equity_ratio = serializers.ReadOnlyField()
    return_on_assets = serializers.ReadOnlyField()

    class Meta:
        model = CompanyFinancialStatement
        fields = [
            'id', 'year', 'total_assets', 'total_liabilities', 'total_equity',
            'gross_profit', 'profit_before_tax', 'audit_report',
            'current_assets', 'current_liabilities', 'cash_and_bank',
            'total_revenue', 'current_ratio', 'cash_ratio', 'working_capital',
            'gross_profit_margin', 'debt_to_equity_ratio', 'return_on_assets',
            'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']

class CompanyLitigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyLitigation
        fields = [
            'id', 'case_number', 'description', 'status', 'filed_date',
            'resolution_date', 'outcome', 'amount_involved', 'currency',
            'proof', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']

class CompanyPersonnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyPersonnel
        fields = [
            'uuid', 'first_name', 'last_name', 'position', 'email', 'phone_number',
            'years_of_experience', 'qualifications', 'education_level', 'age',
            'nationality', 'professional_certifications', 'is_verified', 'resume',
            'uploaded_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'is_verified', 'uploaded_at', 'updated_at']

class CompanyExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyExperience
        fields = [
            'id', 'title', 'description', 'contract_count', 'total_value', 'currency',
            'start_date', 'end_date', 'client_name', 'proof', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({"end_date": "End date must be after start date."})
        return attrs

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
    accounts_company_users = CompanyUserSerializer(many=True, read_only=True)
    accounts_invitations = CompanyInvitationSerializer(many=True, read_only=True)
    accounts_documents = CompanyDocumentSerializer(many=True, read_only=True)
    accounts_offices = CompanyOfficeSerializer(many=True, read_only=True)
    accounts_certifications = CompanyCertificationSerializer(many=True, read_only=True)
    accounts_sources_of_funds = CompanySourceOfFundSerializer(many=True, read_only=True)
    accounts_annual_turnovers = CompanyAnnualTurnoverSerializer(many=True, read_only=True)
    accounts_financial_statements = CompanyFinancialStatementSerializer(many=True, read_only=True)
    accounts_litigations = CompanyLitigationSerializer(many=True, read_only=True)
    accounts_personnel = CompanyPersonnelSerializer(many=True, read_only=True)
    accounts_experiences = CompanyExperienceSerializer(many=True, read_only=True)
    accounts_bids = CompanyBidSerializer(many=True, read_only=True, source='bids_bids')

    class Meta:
        model = Company
        depth = 1
        fields = (
            'id', 'name', 'slug', 'description', 'industry', 'website', 'logo',
            'tax_id', 'registration_number', 'founded_date', 'country',
            'key_activities', 'naics_code', 'status', 'is_verified',
            'verification_date', 'employee_count', 'parent_company',
            'owner', 'owner_email', 'deleted_at', 'created_at', 'updated_at', 'created_by',
            'accounts_company_users', 'accounts_invitations', 'accounts_documents',
            'accounts_offices', 'accounts_certifications', 'accounts_sources_of_funds',
            'accounts_annual_turnovers', 'accounts_financial_statements',
            'accounts_litigations', 'accounts_personnel', 'accounts_experiences',
            'accounts_bids'
        )
        read_only_fields = (
            'slug', 'deleted_at', 'created_at', 'updated_at',
            'accounts_company_users', 'accounts_invitations', 'accounts_documents',
            'accounts_offices', 'accounts_certifications', 'accounts_sources_of_funds',
            'accounts_annual_turnovers', 'accounts_financial_statements',
            'accounts_litigations', 'accounts_personnel', 'accounts_experiences',
            'accounts_bids'
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
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser', 'companies'
        ]
        read_only_fields = fields

    def get_companies(self, obj):
        qs = Company.objects.filter(
            Q(owner=obj) | Q(accounts_company_users__user=obj),
            deleted_at__isnull=True
        ).distinct().select_related('owner')
        return CompanySerializer(qs, many=True, context=self.context).data

class AuditLogSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'user', 'timestamp', 'details']
        read_only_fields = fields