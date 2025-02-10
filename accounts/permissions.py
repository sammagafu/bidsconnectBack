# permissions.py
from rest_framework import permissions
from .models import Company, CompanyUser

class IsCompanyOwner(permissions.BasePermission):
    """Allows access only to company owners"""
    def has_permission(self, request, view):
        # Check for company ownership in URL-based views
        if 'company_id' in view.kwargs:
            company = Company.objects.get(pk=view.kwargs['company_id'])
            return company.owner == request.user
        return True  # Fallback to object-level permission

    def has_object_permission(self, request, view, obj):
        # Handle different object types
        if isinstance(obj, Company):
            return obj.owner == request.user
        if hasattr(obj, 'company'):
            return obj.company.owner == request.user
        return False

class IsCompanyAdminOrOwner(permissions.BasePermission):
    """Allows company admins and owners"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        if 'company_id' in view.kwargs:
            company = Company.objects.get(pk=view.kwargs['company_id'])
            return CompanyUser.objects.filter(
                company=company,
                user=request.user,
                role__in=['owner', 'admin']
            ).exists()
        return True

    def has_object_permission(self, request, view, obj):
        company = obj.company if hasattr(obj, 'company') else obj
        return CompanyUser.objects.filter(
            company=company,
            user=request.user,
            role__in=['owner', 'admin']
        ).exists()

class IsCompanyMember(permissions.BasePermission):
    """Allows any company member"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        if 'company_id' in view.kwargs:
            return CompanyUser.objects.filter(
                company_id=view.kwargs['company_id'],
                user=request.user
            ).exists()
        return True

    def has_object_permission(self, request, view, obj):
        company = obj.company if hasattr(obj, 'company') else obj
        return CompanyUser.objects.filter(
            company=company,
            user=request.user
        ).exists()