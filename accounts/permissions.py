# accounts/permissions.py

from rest_framework import permissions
from django.shortcuts import get_object_or_404
from .models import Company, CompanyUser


class IsCompanyOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        cid = view.kwargs.get('company_id') or view.kwargs.get('id')
        if cid:
            comp = get_object_or_404(Company, id=cid, deleted_at__isnull=True)
            return request.user.is_authenticated and comp.owner == request.user
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        comp = obj.company if hasattr(obj, 'company') else obj
        return (
            request.user.is_authenticated and
            comp.owner == request.user and
            comp.deleted_at is None
        )


class IsCompanyAdminOrOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        cid = view.kwargs.get('company_id')
        if cid:
            comp = get_object_or_404(Company, id=cid, deleted_at__isnull=True)
            return request.user.is_authenticated and CompanyUser.objects.filter(
                company=comp, user=request.user, role__in=['owner', 'admin']
            ).exists()
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        comp = obj.company if hasattr(obj, 'company') else obj
        return (
            request.user.is_authenticated and
            comp.deleted_at is None and
            CompanyUser.objects.filter(
                company=comp, user=request.user, role__in=['owner', 'admin']
            ).exists()
        )


class IsCompanyMember(permissions.BasePermission):
    def has_permission(self, request, view):
        cid = view.kwargs.get('company_id')
        if cid:
            return (
                request.user.is_authenticated and
                CompanyUser.objects.filter(
                    company_id=cid, company__deleted_at__isnull=True, user=request.user
                ).exists()
            )
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        comp = obj.company if hasattr(obj, 'company') else obj
        return (
            request.user.is_authenticated and
            comp.deleted_at is None and
            CompanyUser.objects.filter(
                company=comp, user=request.user
            ).exists()
        )
