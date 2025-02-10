from rest_framework import serializers
from djoser.serializers import UserCreateSerializer
from django.utils import timezone
from .models import CustomUser, Company, CompanyUser, CompanyInvitation, CompanyDocument
from .permissions import IsCompanyAdminOrOwner

class CustomUserCreateSerializer(UserCreateSerializer):
    invitation_token = serializers.CharField(required=False, write_only=True)
    phone_number = serializers.CharField(required=True, min_length=10, max_length=20)

    class Meta(UserCreateSerializer.Meta):
        model = CustomUser
        fields = ('id', 'email', 'phone_number', 'password', 'invitation_token')
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_invitation_token(self, value):
        if value:
            if not CompanyInvitation.objects.filter(token=value).exists():
                raise serializers.ValidationError("Invalid invitation token.")
        return value

    def create(self, validated_data):
        invitation_token = validated_data.pop('invitation_token', None)
        user = super().create(validated_data)
        
        if invitation_token:
            try:
                invitation = CompanyInvitation.objects.select_related('company').get(
                    token=invitation_token,
                    invited_email=user.email,
                    accepted=False,
                    expires_at__gt=timezone.now()
                )
                
                # Create company membership
                CompanyUser.objects.create(
                    company=invitation.company,
                    user=user,
                    role=invitation.role
                )
                
                # Mark invitation as accepted
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

    class Meta:
        model = Company
        fields = (
            'id', 'name', 'slug', 'address', 'city', 'state', 'postal_code', 
            'country', 'description', 'business_license', 
            'tax_identification_number', 'website', 'logo', 'created_at', 'owner'
        )
        read_only_fields = ('created_at',)

    def validate_name(self, value):
        if Company.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("A company with this name already exists.")
        return value

class CompanyUserSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = CompanyUser
        fields = ('id', 'company', 'user', 'user_email', 'company_name', 'role')
        read_only_fields = ('id', 'company', 'user', 'user_email', 'company_name')

    def validate_role(self, value):
        if self.instance and self.instance.role == 'owner':
            if value != 'owner':
                raise serializers.ValidationError("Cannot change owner's role.")
        return value

class CompanyInvitationSerializer(serializers.ModelSerializer):
    invited_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = CompanyInvitation
        fields = ('id', 'company', 'invited_email', 'role', 'invited_by')
        read_only_fields = ('id', 'invited_by')

    def validate(self, attrs):
        user = self.context['request'].user
        company = attrs['company']
        
        # Check inviter permissions
        if not IsCompanyAdminOrOwner().has_object_permission(
            self.context['request'], self, company
        ):
            raise serializers.ValidationError(
                "You don't have permission to invite users to this company."
            )

        # Check existing users
        if CompanyUser.objects.filter(
            company=company,
            user__email=attrs['invited_email']
        ).exists():
            raise serializers.ValidationError(
                "This user is already part of the company."
            )

        # Check pending invitations
        if CompanyInvitation.objects.filter(
            company=company,
            invited_email=attrs['invited_email'],
            accepted=False
        ).exists():
            raise serializers.ValidationError(
                "An invitation is already pending for this email."
            )

        # Role validation
        if attrs['role'] == 'owner':
            raise serializers.ValidationError(
                "Cannot invite users as owners. Owner status is automatic."
            )

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
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds maximum allowed size of {max_size//1024//1024}MB"
            )
        return value

    def create(self, validated_data):
        validated_data['company_id'] = self.context['view'].kwargs['company_id']
        return super().create(validated_data)