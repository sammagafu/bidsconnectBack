from rest_framework import serializers
from djoser.serializers import UserCreateSerializer
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, Company, CompanyUser, CompanyInvitation, CompanyDocument
from .permissions import IsCompanyAdminOrOwner
from .constants import ROLE_CHOICES, VALID_FILE_EXTENSIONS, MAX_FILE_SIZE
import os
from django.db.models import Q

# Existing serializers (unchanged)
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'phone_number', 'first_name', 'last_name']
        read_only_fields = ['id', 'email']

class CustomUserCreateSerializer(UserCreateSerializer):
    invitation_token = serializers.CharField(required=False, write_only=True)
    phone_number = serializers.CharField(required=True, min_length=10, max_length=20)

    class Meta(UserCreateSerializer.Meta):
        model = CustomUser
        fields = ('id', 'email', 'phone_number', 'password', 'invitation_token','first_name', 'last_name')
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_invitation_token(self, value):
        if value and not CompanyInvitation.objects.filter(token=value).exists():
            raise serializers.ValidationError({"invitation_token": "Invalid invitation token."})
        return value

    def create(self, validated_data):
        invitation_token = validated_data.pop('invitation_token', None)
        phone_number = validated_data.pop('phone_number', None)
        
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        if phone_number:
            user.phone_number = phone_number
            user.save()
        
        if invitation_token:
            try:
                invitation = CompanyInvitation.objects.select_related('company').get(
                    token=invitation_token,
                    invited_email=user.email,
                    accepted=False,
                    expires_at__gt=timezone.now()
                )
                CompanyUser.objects.create(
                    company=invitation.company,
                    user=user,
                    role=invitation.role
                )
                invitation.accepted = True
                invitation.save(update_fields=['accepted'])
            except CompanyInvitation.DoesNotExist:
                raise serializers.ValidationError({
                    'invitation_token': 'Invalid or expired invitation token.'
                })
        return user

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(min_length=10, max_length=20)

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'phone_number')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

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
            'id', 'name', 'slug', 'description', 'industry', 'website', 'logo',
            'email', 'phone_number', 'address', 'tax_id', 'registration_number',
            'founded_date', 'country', 'status', 'employee_count', 'parent_company',
            'owner', 'owner_email','is_verified','verification_date', 'created_at', 'updated_at', 'created_by'
        )
        read_only_fields = ('created_at', 'updated_at')

    def get_owner_email(self, obj):
        return obj.owner.email

    def validate_name(self, value):
        if Company.objects.filter(name__iexact=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError({"name": "A company with this name already exists."})
        return value

class CompanyUserSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())

    class Meta:
        model = CompanyUser
        fields = ('id', 'company', 'user', 'user_email', 'company_name', 'role')
        read_only_fields = ('id', 'company', 'user_email', 'company_name')

    def validate_role(self, value):
        if self.instance and self.instance.role == 'owner' and value != 'owner':
            raise serializers.ValidationError({"role": "Cannot change owner's role."})
        return value

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
        user = self.context['request'].user
        company_id = self.context['view'].kwargs.get('company_id')
        if not company_id:
            raise serializers.ValidationError({"company": "Company ID must be provided in the URL."})
        
        company = Company.objects.get(id=company_id, deleted_at__isnull=True)
        
        if not IsCompanyAdminOrOwner().has_object_permission(self.context['request'], self, company):
            raise serializers.ValidationError({"company": "You don't have permission to invite users to this company."})

        if CompanyUser.objects.filter(company=company, user__email=attrs['invited_email']).exists():
            raise serializers.ValidationError({"invited_email": "This user is already part of the company."})

        if CompanyInvitation.objects.filter(
            company=company,
            invited_email=attrs['invited_email'],
            accepted=False
        ).exists():
            raise serializers.ValidationError({"invited_email": "An invitation is already pending for this email."})

        if attrs['role'] == 'owner':
            raise serializers.ValidationError({"role": "Cannot invite users as owners."})

        attrs['company'] = company
        return attrs

class CompanyDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = CompanyDocument
        fields = ('id', 'company', 'document_type', 'document_file', 'uploaded_at', 'uploaded_by')
        read_only_fields = ('uploaded_at', 'uploaded_by')
        extra_kwargs = {
            'company': {'read_only': True},
        }

    def validate_document_file(self, value):
        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError({"document_file": f"File size exceeds maximum allowed size of {MAX_FILE_SIZE//1024//1024}MB"})
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in VALID_FILE_EXTENSIONS:
            raise serializers.ValidationError({"document_file": "Unsupported file format."})
        return value

    def create(self, validated_data):
        validated_data['company_id'] = self.context['view'].kwargs['company_id']
        return super().create(validated_data)

# Updated CustomUserDetailSerializer
class CustomUserDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed user data with all nested relationships"""
    companies = serializers.SerializerMethodField()
    company_users = serializers.SerializerMethodField()
    invitations_sent = serializers.SerializerMethodField()
    invitations_received = serializers.SerializerMethodField()
    documents_uploaded = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser',  # Added comma here
            'companies', 'company_users', 'invitations_sent', 'invitations_received', 'documents_uploaded'
        ]
        read_only_fields = ['id', 'email', 'is_active', 'is_staff']

    def get_companies(self, obj):
        """Get all companies where the user is the owner or a member"""
        companies = Company.objects.filter(
            Q(owner=obj) | Q(company_users__user=obj),
            deleted_at__isnull=True
        ).distinct()
        return CompanySerializer(companies, many=True, context=self.context).data

    def get_company_users(self, obj):
        """Get all CompanyUser instances for the user"""
        company_users = CompanyUser.objects.filter(
            user=obj,
            company__deleted_at__isnull=True
        ).select_related('company')
        return CompanyUserSerializer(company_users, many=True, context=self.context).data

    def get_invitations_sent(self, obj):
        """Get all invitations sent by the user"""
        invitations = CompanyInvitation.objects.filter(
            invited_by=obj,
            company__deleted_at__isnull=True,
            expires_at__gt=timezone.now()
        ).select_related('company')
        return CompanyInvitationSerializer(invitations, many=True, context=self.context).data

    def get_invitations_received(self, obj):
        """Get all pending invitations received by the user"""
        invitations = CompanyInvitation.objects.filter(
            invited_email=obj.email,
            accepted=False,
            expires_at__gt=timezone.now(),
            company__deleted_at__isnull=True
        ).select_related('company')
        return CompanyInvitationSerializer(invitations, many=True, context=self.context).data

    def get_documents_uploaded(self, obj):
        """Get all documents uploaded by the user"""
        documents = CompanyDocument.objects.filter(
            uploaded_by=obj,
            company__deleted_at__isnull=True
        ).select_related('company')
        return CompanyDocumentSerializer(documents, many=True, context=self.context).data