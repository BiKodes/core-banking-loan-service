"""
Common Module - Multitenancy and Organization Management

This module provides the core multitenancy infrastructure for the Core Banking Loan Service.
All data in the system is organization-scoped, ensuring complete data isolation between tenants.
"""

from .models import (
    Organization,
    OrganizationUser,
    TenantAwareModel,
    TenantAwareManager,
    TenantAwareQuerySet,
)
from .middleware import OrganizationMiddleware
from .permissions import (
    IsOrganizationMember,
    HasOrganizationPermission,
    IsAdminOnly,
    IsManagerOrAbove,
    IsAccountantOrAbove,
    IsViewerOrAbove,
    CanModifyOrganizationData,
    CanViewOrganizationReports,
)
from .utils import (
    get_organization_from_request,
    require_organization,
    filter_queryset_for_organization,
    get_user_organizations,
    get_user_role_in_organization,
    user_has_role_in_organization,
    add_user_to_organization,
    remove_user_from_organization,
    get_organization_statistics,
)
from .apps import CommonConfig

__all__ = [
    # Models
    'Organization',
    'OrganizationUser',
    'TenantAwareModel',
    'TenantAwareManager',
    'TenantAwareQuerySet',
    # Middleware
    'OrganizationMiddleware',
    # Permissions
    'IsOrganizationMember',
    'HasOrganizationPermission',
    'IsAdminOnly',
    'IsManagerOrAbove',
    'IsAccountantOrAbove',
    'IsViewerOrAbove',
    'CanModifyOrganizationData',
    'CanViewOrganizationReports',
    # Utilities
    'get_organization_from_request',
    'require_organization',
    'filter_queryset_for_organization',
    'get_user_organizations',
    'get_user_role_in_organization',
    'user_has_role_in_organization',
    'add_user_to_organization',
    'remove_user_from_organization',
    'get_organization_statistics',
    # Apps
    'CommonConfig',
]
