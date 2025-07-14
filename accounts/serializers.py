import os
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from .models import (
    CustomUser, Company, CompanyUser, CompanyInvitation, CompanyDocument
)
from .constants import VALID_FILE_EXTENSIONS, MAX_FILE_SIZE, MAX_COMPANIES_PER_USER, MAX_COMPANY_USERS
from .permissions import IsCompanyAdminOrOwner


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
        first = validated_data.get('first_name', '')
        last = validated_data.get('last_name', '')

        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=first,
            last_name=last
        )
        user.phone_number = phone
        user.save(update_fields=['phone_number'])

        if token:
            invitation = get_object_or_404(
                CompanyInvitation,
                token=token,
                invited_email=user.email,
                accepted=False,
                expires_at__gt=timezone.now(),
                company__deleted_at__isnull=True
            )
            # Enforce max members when accepting
            company = invitation.company
            if company.company_users.count() >= MAX_COMPANY_USERS:
                raise serializers.ValidationError(
                    "Cannot accept invitation: company already has maximum members."
                )
            CompanyUser.objects.create(
                company=company,
                user=user,
                role=invitation.role
            )
            invitation.accepted = True
            invitation.save(update_fields=['accepted'])
        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(read_only=True)
    phone_number = serializers.CharField(min_length=10, max_length=20)

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'phone_number')


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
        fields = (
            'id', 'name', 'slug', 'description', 'industry',
            'website', 'logo', 'email', 'phone_number',
            'address', 'tax_id', 'registration_number',
            'founded_date', 'country', 'status',
            'is_verified', 'verification_date', 'employee_count',
            'parent_company', 'owner', 'owner_email',
            'deleted_at', 'created_at', 'updated_at',
            'created_by'
        )
        read_only_fields = ('deleted_at', 'created_at', 'updated_at')

    def get_owner_email(self, obj):
        return obj.owner.email

    def validate(self, attrs):
        request = self.context['request']
        user = request.user
        # Ensure one company per user on create
        if self.instance is None and Company.objects.filter(
            owner=user, deleted_at__isnull=True
        ).exists():
            raise serializers.ValidationError(
                { 'owner': f"A user can only own {MAX_COMPANIES_PER_USER} company." }
            )
        return attrs

    def validate_name(self, value):
        if Company.objects.filter(
            name__iexact=value, deleted_at__isnull=True
        ).exists():
            raise serializers.ValidationError(
                "A company with this name already exists."
            )
        return value


class CompanyUserSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = CompanyUser
        fields = ('id', 'user', 'user_email', 'role')
        read_only_fields = ('id', 'user_email')

    def validate(self, attrs):
        request = self.context.get('request')
        view = self.context.get('view')
        # Determine company from URL kwargs
        company_id = view.kwargs.get('company_id')
        company = get_object_or_404(Company, id=company_id, deleted_at__isnull=True)
        # On create, enforce max members
        if self.instance is None:
            if company.company_users.count() >= MAX_COMPANY_USERS:
                raise serializers.ValidationError(
                    f"A company can only have up to {MAX_COMPANY_USERS} members."
                )
        # Prevent demoting owner
        if self.instance and self.instance.role == 'owner' and attrs.get('role') != 'owner':
            raise serializers.ValidationError("Cannot change owner's role.")
        return attrs

    def create(self, validated_data):
        view = self.context.get('view')
        company_id = view.kwargs.get('company_id')
        validated_data['company'] = get_object_or_404(
            Company, id=company_id, deleted_at__isnull=True
        )
        return super().create(validated_data)


class CompanyInvitationSerializer(serializers.ModelSerializer):
    invited_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.filter(deleted_at__isnull=True),
        required=False
    )

    class Meta:
        model = CompanyInvitation
        fields = ('id', 'company', 'invited_email', 'role', 'invited_by')
        read_only_fields = ('id', 'invited_by')

    def validate(self, attrs):
        request = self.context['request']
        view = self.context['view']
        cid = view.kwargs.get('company_id')
        if not cid:
            raise serializers.ValidationError({"company": "Company ID is required in URL."})
        company = get_object_or_404(Company, id=cid, deleted_at__isnull=True)
        # Permission check
        if not IsCompanyAdminOrOwner().has_permission(request, view):
            raise serializers.ValidationError(
                {"company": "No permission to invite to this company."}
            )
        # Already a member
        if CompanyUser.objects.filter(company=company, user__email=attrs['invited_email']).exists():
            raise serializers.ValidationError(
                {"invited_email": "User already in this company."}
            )
        # Pending invitation
        if CompanyInvitation.objects.filter(
            company=company, invited_email=attrs['invited_email'], accepted=False
        ).exists():
            raise serializers.ValidationError(
                {"invited_email": "An invitation is already pending."}
            )
        # Cannot invite owner
        if attrs['role'] == 'owner':
            raise serializers.ValidationError({"role": "Cannot invite an owner."})
        # Max members per company
        if company.company_users.count() >= MAX_COMPANY_USERS:
            raise serializers.ValidationError(
                {"company": f"A company can only have up to {MAX_COMPANY_USERS} members."}
            )
        attrs['company'] = company
        return attrs


class CompanyDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = CompanyDocument
        fields = (
            'id', 'company', 'document_type', 'document_category',
            'document_file', 'uploaded_at', 'expires_at', 'uploaded_by'
        )
        read_only_fields = ('id', 'uploaded_at', 'uploaded_by')
        extra_kwargs = {'company': {'read_only': True}}

    def validate_document_file(self, file):
        if file.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f"Max file size is {MAX_FILE_SIZE//(1024*1024)}MB"
            )
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in VALID_FILE_EXTENSIONS:
            raise serializers.ValidationError("Unsupported file format.")
        return file

    def create(self, validated_data):
        view = self.context['view']
        company = get_object_or_404(
            Company, id=view.kwargs['company_id'], deleted_at__isnull=True
        )
        validated_data['company'] = company
        return super().create(validated_data)


class CompanyNestedSerializer(CompanySerializer):
    company_users = CompanyUserSerializer(many=True, read_only=True)
    documents = CompanyDocumentSerializer(many=True, read_only=True)

    class Meta(CompanySerializer.Meta):
        fields = CompanySerializer.Meta.fields + ('company_users', 'documents')


class CustomUserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed user endpoint for GET /users/me/ includes nested companies with users and documents
    """
    companies = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser',
            'companies'
        ]
        read_only_fields = fields

    def get_companies(self, obj):
        qs = Company.objects.filter(
            Q(owner=obj) | Q(company_users__user=obj),
            deleted_at__isnull=True
        ).distinct()
        return CompanyNestedSerializer(qs, many=True, context=self.context).data
