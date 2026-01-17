"""
Organization-based Permissions and Authentication

Provides permission classes for enforcing organization-based access control
in DRF viewsets and views.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import OrganizationUser


class IsOrganizationMember(IsAuthenticated):
    """
    Permission class that ensures:
    1. User is authenticated
    2. User is a member of the requested organization
    3. The user-organization mapping is active
    """

    def has_permission(self, request, view):
        """
        Check if user is authenticated and is a member of the organization.
        """
        if not super().has_permission(request, view):
            return False

        if not hasattr(request, 'organization') or request.organization is None:
            return False

        is_member = OrganizationUser.objects.filter(
            user=request.user, organization=request.organization, is_active=True
        ).exists()

        return is_member


class HasOrganizationPermission(IsOrganizationMember):
    """
    Permission class that enforces role-based access control.

    Subclass this and set REQUIRED_ROLE to enforce specific roles.
    """

    REQUIRED_ROLE = None

    def has_permission(self, request, view):
        """
        Check if user has required role in the organization.

        """
        if not super().has_permission(request, view):
            return False

        if self.REQUIRED_ROLE is None:
            return True

        org_user = OrganizationUser.objects.filter(
            user=request.user, organization=request.organization, is_active=True
        ).first()

        if not org_user:
            return False

        role_hierarchy = {
            'viewer': 0,
            'user': 1,
            'accountant': 2,
            'manager': 3,
            'admin': 4,
        }

        user_role_level = role_hierarchy.get(org_user.role, -1)
        required_role_level = role_hierarchy.get(self.REQUIRED_ROLE, -1)

        return user_role_level >= required_role_level


class IsAdminOnly(HasOrganizationPermission):
    """Permission class for admin-only endpoints."""

    REQUIRED_ROLE = 'admin'


class IsManagerOrAbove(HasOrganizationPermission):
    """Permission class for manager-level or above endpoints."""

    REQUIRED_ROLE = 'manager'


class IsAccountantOrAbove(HasOrganizationPermission):
    """Permission class for accountant-level or above endpoints."""

    REQUIRED_ROLE = 'accountant'


class IsViewerOrAbove(HasOrganizationPermission):
    """Permission class for viewer-level or above endpoints."""

    REQUIRED_ROLE = 'viewer'


class CanModifyOrganizationData(BasePermission):
    """
    Permission class that ensures:
    1. User is authenticated
    2. User is a member of the organization
    3. User's role allows modification (admin, manager, accountant, or user)
    4. Data belongs to the user's organization
    """

    MODIFIABLE_ROLES = ['admin', 'manager', 'accountant', 'user']

    def has_permission(self, request, view):
        """Check if user can modify data in their organization."""

        if not request.user or not request.user.is_authenticated:
            return False

        if not hasattr(request, 'organization') or request.organization is None:
            return False

        org_user = OrganizationUser.objects.filter(
            user=request.user, organization=request.organization, is_active=True
        ).first()

        if not org_user:
            return False

        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        return org_user.role in self.MODIFIABLE_ROLES

    def has_object_permission(self, request, view, obj):
        """Ensure object belongs to user's organization."""

        if hasattr(obj, 'organization_id'):
            return obj.organization_id == request.organization_id

        return True


class CanViewOrganizationReports(BasePermission):
    """
    Permission class for viewing reports.
    """

    def has_permission(self, request, view):
        """Check if user can view reports."""

        if not request.user or not request.user.is_authenticated:
            return False

        if not hasattr(request, 'organization') or request.organization is None:
            return False

        org_user = OrganizationUser.objects.filter(
            user=request.user, organization=request.organization, is_active=True
        ).first()

        if not org_user:
            return False

        viewable_roles = ['admin', 'manager', 'accountant', 'viewer']
        return org_user.role in viewable_roles


__all__ = [
    'IsOrganizationMember',
    'HasOrganizationPermission',
    'IsAdminOnly',
    'IsManagerOrAbove',
    'IsAccountantOrAbove',
    'IsViewerOrAbove',
    'CanModifyOrganizationData',
    'CanViewOrganizationReports',
]
