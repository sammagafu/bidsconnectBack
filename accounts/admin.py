from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, Company, CompanyUser, CompanyInvitation, CompanyDocument, AuditLog

# CustomUser Admin
class CustomUserAdmin(BaseUserAdmin):
    model = CustomUser
    list_display = ('email', 'phone_number', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email', 'phone_number', 'first_name', 'last_name')
    ordering = ('email',)
    
    # Fields to display in the admin form
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('phone_number', 'first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone_number', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    # No readonly_fields like 'date_joined' or 'last_login' since they don’t exist

# Company Admin
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_by', 'status', 'created_at', 'deleted_at')
    list_filter = ('status', 'created_at', 'deleted_at')
    search_fields = ('name', 'owner__email', 'created_by__email', 'slug')
    raw_id_fields = ('owner', 'created_by', 'parent_company')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('name', 'slug', 'owner', 'created_by')}),
        ('Details', {'fields': ('description', 'industry', 'website', 'logo', 'email', 'phone_number', 'address')}),
        ('Legal', {'fields': ('tax_id', 'registration_number', 'founded_date', 'country')}),
        ('Operational', {'fields': ('status', 'employee_count', 'parent_company')}),
        ('Metadata', {'fields': ('created_at', 'updated_at', 'deleted_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')

# CompanyUser Admin
@admin.register(CompanyUser)
class CompanyUserAdmin(admin.ModelAdmin):
    list_display = ('company', 'user', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('company__name', 'user__email')
    raw_id_fields = ('company', 'user')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

# CompanyInvitation Admin
@admin.register(CompanyInvitation)
class CompanyInvitationAdmin(admin.ModelAdmin):
    list_display = ('company', 'invited_email', 'role', 'invited_by', 'accepted', 'created_at', 'expires_at')
    list_filter = ('accepted', 'role', 'created_at', 'expires_at')
    search_fields = ('company__name', 'invited_email', 'invited_by__email')
    raw_id_fields = ('company', 'invited_by')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('company', 'invited_email', 'role', 'invited_by')}),
        ('Status', {'fields': ('accepted', 'token', 'created_at', 'expires_at')}),
    )
    readonly_fields = ('token', 'created_at')

# CompanyDocument Admin
@admin.register(CompanyDocument)
class CompanyDocumentAdmin(admin.ModelAdmin):
    list_display = ('company', 'document_type', 'uploaded_by', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('company__name', 'uploaded_by__email')
    raw_id_fields = ('company', 'uploaded_by')
    date_hierarchy = 'uploaded_at'
    ordering = ('-uploaded_at',)

    fieldsets = (
        (None, {'fields': ('company', 'document_type', 'document_file')}),
        ('Metadata', {'fields': ('uploaded_by', 'uploaded_at')}),
    )
    readonly_fields = ('uploaded_at',)

# AuditLog Admin
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'timestamp', 'details')
    list_filter = ('action', 'timestamp')
    search_fields = ('action', 'user__email', 'details')
    raw_id_fields = ('user',)
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)

    fieldsets = (
        (None, {'fields': ('action', 'user', 'details')}),
        ('Metadata', {'fields': ('timestamp',)}),
    )
    readonly_fields = ('timestamp',)

# Register CustomUser with the admin site
admin.site.register(CustomUser, CustomUserAdmin)