from rest_framework import permissions
from .models import Company, CompanyUser

class IsCompanyOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.is_active:
            return False

        if 'company_id' in view.kwargs:
            company = Company.objects.get(id=view.kwargs['company_id'], deleted_at__isnull=True)
            return company.owner == request.user
        return True

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Company):
            return obj.owner == request.user and obj.deleted_at is None
        if hasattr(obj, 'company'):
            return obj.company.owner == request.user and obj.company.deleted_at is None
        return False

class IsCompanyAdminOrOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.is_active:
            return False
            
        if 'company_id' in view.kwargs:
            company = Company.objects.get(id=view.kwargs['company_id'], deleted_at__isnull=True)
            return CompanyUser.objects.filter(
                company=company,
                user=request.user,
                role__in=['owner', 'admin']
            ).exists()
        return True

    def has_object_permission(self, request, view, obj):
        company = obj.company if hasattr(obj, 'company') else obj
        return company.deleted_at is None and CompanyUser.objects.filter(
            company=company,
            user=request.user,
            role__in=['owner', 'admin']
        ).exists()

class IsCompanyMember(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.is_active:
            return False
            
        if 'company_id' in view.kwargs:
            return CompanyUser.objects.filter(
                company_id=view.kwargs['company_id'],
                company__deleted_at__isnull=True,
                user=request.user
            ).exists()
        return True

    def has_object_permission(self, request, view, obj):
        company = obj.company if hasattr(obj, 'company') else obj
        return company.deleted_at is None and CompanyUser.objects.filter(
            company=company,
            user=request.user
        ).exists()