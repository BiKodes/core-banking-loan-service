"""
Organization Utility Functions

Helper functions for working with organizations and managing multitenancy.
"""

from functools import wraps
from django.core.exceptions import ValidationError
from .models import Organization, OrganizationUser


def get_organization_from_request(request):
    """
    Extract organization from request context.
    """
    return getattr(request, 'organization', None)


def require_organization(view_func):
    """
    Decorator that ensures a view has a valid organization context.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'organization') or request.organization is None:
            from django.http import JsonResponse
            return JsonResponse(
                {'error': 'Organization context required'},
                status=400
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def filter_queryset_for_organization(queryset, organization):
    """
    Filter a queryset for a specific organization.
    
    Works with TenantAwareModel subclasses.
    """
    if hasattr(queryset, 'for_organization'):
        return queryset.for_organization(organization)
    
    if isinstance(organization, int):
        return queryset.filter(organization_id=organization)
    return queryset.filter(organization=organization)


def get_user_organizations(user, active_only=True):
    """
    Get all organizations a user belongs to.
    """
    queryset = Organization.objects.filter(
        users__user=user,
        users__is_active=True
    ).distinct()
    
    if active_only:
        queryset = queryset.filter(is_active=True)
    
    return queryset


def get_user_role_in_organization(user, organization):
    """
    Get a user's role in a specific organization.
    """
    org_user = OrganizationUser.objects.filter(
        user=user,
        organization=organization,
        is_active=True
    ).first()
    
    return org_user.role if org_user else None


def user_has_role_in_organization(user, organization, role):
    """
    Check if a user has a specific role (or higher) in an organization.
    """
    user_role = get_user_role_in_organization(user, organization)
    
    if user_role is None:
        return False
    
    role_hierarchy = {
        'viewer': 0,
        'user': 1,
        'accountant': 2,
        'manager': 3,
        'admin': 4,
    }
    
    user_level = role_hierarchy.get(user_role, -1)
    required_level = role_hierarchy.get(role, -1)
    
    return user_level >= required_level


def add_user_to_organization(user, organization, role='user'):
    """
    Add a user to an organization with a specific role.
    
    Creates OrganizationUser record for the user-organization pair.
    If the user already exists in the organization, updates their role.
    """
    
    valid_roles = ['admin', 'manager', 'accountant', 'viewer', 'user']
    if role not in valid_roles:
        raise ValidationError(f"Invalid role: {role}. Must be one of {valid_roles}")
    
    if not organization.is_active:
        raise ValidationError(f"Cannot add user to inactive organization: {organization.code}")
    
    org_user, created = OrganizationUser.objects.update_or_create(
        user=user,
        organization=organization,
        defaults={
            'role': role,
            'is_active': True
        }
    )
    
    return org_user, created


def remove_user_from_organization(user, organization):
    """
    Remove a user from an organization (soft delete).
    
    Sets is_active=False instead of deleting the record, preserving history.
    """
    try:
        org_user = OrganizationUser.objects.get(user=user, organization=organization)
        org_user.is_active = False
        org_user.save()
        return True
    except OrganizationUser.DoesNotExist:
        return False


def get_organization_statistics(organization):
    """
    Get basic statistics for an organization.
    """
    stats = {
        'organization_code': organization.code,
        'organization_name': organization.name,
        'is_active': organization.is_active,
        'user_count': OrganizationUser.objects.filter(
            organization=organization,
            is_active=True
        ).count(),
        'admin_count': OrganizationUser.objects.filter(
            organization=organization,
            role='admin',
            is_active=True
        ).count(),
        'created_at': organization.created_at,
        'updated_at': organization.updated_at,
    }
    return stats


__all__ = [
    'get_organization_from_request',
    'require_organization',
    'filter_queryset_for_organization',
    'get_user_organizations',
    'get_user_role_in_organization',
    'user_has_role_in_organization',
    'add_user_to_organization',
    'remove_user_from_organization',
    'get_organization_statistics',
]
