"""
Common Module - Multitenancy and Organization Management

This module provides the core multitenancy infrastructure for the Core Banking Loan Service.
All data in the system is organization-scoped, ensuring complete data isolation between tenants.

Avoid importing models at module level to prevent AppRegistryNotReady errors
Import these directly from their modules when needed:
    from src.common.models import Organization, OrganizationUser, etc.
    from src.common.middleware import OrganizationMiddleware
    from src.common.permissions import IsOrganizationMember, etc.
    from src.common.utils import get_organization_from_request, etc.
"""

from .apps import CommonConfig

__all__ = [
    'CommonConfig',
]
