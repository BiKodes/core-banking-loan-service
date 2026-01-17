"""
Django Admin Configuration for Multitenancy Models

Provides admin interfaces for managing organizations and organization users.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Organization, OrganizationUser


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """
    Admin interface for Organization model.
    """

    list_display = (
        'code',
        'name',
        'country',
        'city',
        'user_count',
        'is_active',
        'created_at',
    )
    list_filter = ('is_active', 'country', 'created_at')
    search_fields = ('code', 'name', 'email')
    readonly_fields = ('created_at', 'updated_at', 'user_count')

    fieldsets = (
        ('Identification', {'fields': ('code', 'name', 'description')}),
        ('Location', {'fields': ('country', 'city')}),
        ('Contact Information', {'fields': ('phone', 'email')}),
        ('Status', {'fields': ('is_active',)}),
        (
            'Metadata',
            {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)},
        ),
        ('Statistics', {'fields': ('user_count',), 'classes': ('collapse',)}),
    )

    actions = ['activate_organizations', 'deactivate_organizations']

    def user_count(self, obj):
        """Display active user count for the organization."""
        count = obj.users.filter(is_active=True).count()
        return format_html(
            '<span style="background-color: #e7f3ff; padding: 3px 8px; border-radius: 3px;">{}</span>',
            count,
        )

    user_count.short_description = 'Active Users'

    def activate_organizations(self, request, queryset):
        """Admin action to activate organizations."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request, f"{updated} organization(s) activated successfully."
        )

    activate_organizations.short_description = "Activate selected organizations"

    def deactivate_organizations(self, request, queryset):
        """Admin action to deactivate organizations."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request, f"{updated} organization(s) deactivated successfully."
        )

    deactivate_organizations.short_description = (
        "Deactivate selected organizations"
    )


@admin.register(OrganizationUser)
class OrganizationUserAdmin(admin.ModelAdmin):
    """
    Admin interface for OrganizationUser model.
    """

    list_display = (
        'user_name',
        'organization_code',
        'role_display',
        'is_active_display',
        'added_at',
    )
    list_filter = ('organization', 'role', 'is_active', 'added_at')
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'organization__code',
        'organization__name',
    )
    readonly_fields = ('added_at',)
    raw_id_fields = ('user', 'organization')

    fieldsets = (
        ('User and Organization', {'fields': ('user', 'organization')}),
        ('Role and Permissions', {'fields': ('role', 'is_active')}),
        ('Metadata', {'fields': ('added_at',), 'classes': ('collapse',)}),
    )

    actions = [
        'make_admin',
        'make_manager',
        'make_accountant',
        'make_viewer',
        'make_user',
        'activate_users',
        'deactivate_users',
    ]

    def user_name(self, obj):
        """Display full user name with fallback to username."""
        full_name = obj.user.get_full_name()
        return full_name or obj.user.username

    user_name.short_description = 'User'

    def organization_code(self, obj):
        """Display organization code."""
        return obj.organization.code

    organization_code.short_description = 'Organization'

    def role_display(self, obj):
        """Display role with color coding."""
        colors = {
            'admin': '#ff9999',
            'manager': '#ffcc99',
            'accountant': '#99ccff',
            'viewer': '#99ff99',
            'user': '#cccccc',
        }
        color = colors.get(obj.role, '#ffffff')
        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px; color: black;">{}</span>',
            color,
            obj.get_role_display(),
        )

    role_display.short_description = 'Role'

    def is_active_display(self, obj):
        """Display active status with icon."""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active</span>'
            )
        else:
            return format_html('<span style="color: red;">✗ Inactive</span>')

    is_active_display.short_description = 'Status'

    def make_admin(self, request, queryset):
        """Change selected users to admin role."""
        updated = queryset.update(role='admin')
        self.message_user(request, f"{updated} user(s) promoted to admin.")

    make_admin.short_description = "Change to Admin"

    def make_manager(self, request, queryset):
        """Change selected users to manager role."""
        updated = queryset.update(role='manager')
        self.message_user(request, f"{updated} user(s) promoted to manager.")

    make_manager.short_description = "Change to Manager"

    def make_accountant(self, request, queryset):
        """Change selected users to accountant role."""
        updated = queryset.update(role='accountant')
        self.message_user(request, f"{updated} user(s) promoted to accountant.")

    make_accountant.short_description = "Change to Accountant"

    def make_viewer(self, request, queryset):
        """Change selected users to viewer role."""
        updated = queryset.update(role='viewer')
        self.message_user(request, f"{updated} user(s) changed to viewer.")

    make_viewer.short_description = "Change to Viewer"

    def make_user(self, request, queryset):
        """Change selected users to user role."""
        updated = queryset.update(role='user')
        self.message_user(request, f"{updated} user(s) changed to user.")

    make_user.short_description = "Change to User"

    def activate_users(self, request, queryset):
        """Activate selected users."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated.")

    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        """Deactivate selected users."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated.")

    deactivate_users.short_description = "Deactivate selected users"


__all__ = ['OrganizationAdmin', 'OrganizationUserAdmin']
