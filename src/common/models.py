"""
Organization Multitenancy Models

This module defines the core multitenancy models for the Core Banking Loan Service.
All data models inherit from TenantAwareModel to ensure data isolation between organizations.
"""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class Organization(models.Model):
    """
    Represents a tenant organization in the system.

    Each organization is completely isolated - users can only see data
    belonging to their organization.
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique organization code (e.g., ORG001)",
    )
    name = models.CharField(
        max_length=255, help_text="Display name of the organization"
    )
    description = models.TextField(
        blank=True, help_text="Detailed description of the organization"
    )

    country = models.CharField(
        max_length=100, blank=True, help_text="Country of operation"
    )
    city = models.CharField(
        max_length=100, blank=True, help_text="City/Region of operation"
    )

    phone = models.CharField(
        max_length=20, blank=True, help_text="Contact phone number"
    )
    email = models.EmailField(blank=True, help_text="Contact email address")

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether the organization is active",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def __repr__(self):
        return f"<Organization: {self.code}>"


class OrganizationUser(models.Model):
    """
    Maps users to organizations with role-based access control.

    A user can belong to multiple organizations with different roles.
    """

    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('accountant', 'Accountant'),
        ('viewer', 'Viewer'),
        ('user', 'User'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="users",
        help_text="The organization this user belongs to",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="organizations",
        help_text="The Django user",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='user',
        help_text="Role within the organization",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this user is active in this organization",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Organization User"
        verbose_name_plural = "Organization Users"
        unique_together = [['organization', 'user']]
        ordering = ['-added_at']
        indexes = [
            models.Index(fields=['organization', 'user']),
            models.Index(fields=['organization', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.organization.code} ({self.role})"

    def __repr__(self):
        return (
            f"<OrganizationUser: {self.user.username}@{self.organization.code}>"
        )

    def clean(self):
        """Validate the organization user mapping."""
        if not self.is_active and self.organization.is_active:
            pass


class TenantAwareQuerySet(models.QuerySet):
    """
    Custom QuerySet that provides organization filtering.
    """

    def for_organization(self, organization):
        """
        Filter queryset for a specific organization.
        """
        if isinstance(organization, int):
            return self.filter(organization_id=organization)
        return self.filter(organization=organization)

    def active_organizations(self):
        """Filter for records in active organizations."""
        return self.filter(organization__is_active=True)


class TenantAwareManager(models.Manager):
    """
    Custom Manager that returns TenantAwareQuerySet.

    Provides convenience methods for organization-based filtering.
    """

    def get_queryset(self):
        """Return a TenantAwareQuerySet."""
        return TenantAwareQuerySet(self.model, using=self._db)

    def for_organization(self, organization):
        """
        Get records for a specific organization.
        """
        return self.get_queryset().for_organization(organization)

    def active_organizations(self):
        """Get records in active organizations."""
        return self.get_queryset().active_organizations()


class TenantAwareModel(models.Model):
    """
    Abstract base class for all tenant-aware models.

    Ensures every record in the system belongs to exactly one organization.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="%(class)s_records",
        help_text="The organization that owns this record",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['organization', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        """Ensure organization is set before saving."""
        if not self.organization_id:
            raise ValidationError(
                "organization must be set before saving a TenantAwareModel instance"
            )
        super().save(*args, **kwargs)

    def clean(self):
        """Validate that organization is set."""
        super().clean()
        if not self.organization_id:
            raise ValidationError({'organization': 'Organization is required'})


__all__ = [
    'Organization',
    'OrganizationUser',
    'TenantAwareModel',
    'TenantAwareManager',
    'TenantAwareQuerySet',
]
