"""Admin configuration for accounts app."""

from django.contrib import admin
from .models import Account, AccountBalance


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """Admin for Account model."""

    list_display = ['code', 'name', 'account_type', 'currency', 'is_active', 'current_balance']
    list_filter = ['account_type', 'currency', 'is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'version', 'current_balance']
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description')
        }),
        ('Classification', {
            'fields': ('account_type', 'currency')
        }),
        ('Hierarchy', {
            'fields': ('parent',)
        }),
        ('Settings', {
            'fields': ('is_active', 'is_control_account', 'is_system_account', 'identifiers')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'version'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AccountBalance)
class AccountBalanceAdmin(admin.ModelAdmin):
    """Admin for AccountBalance."""

    list_display = ['account', 'balance_date', 'balance', 'debit_total', 'credit_total']
    list_filter = ['balance_date', 'account']
    search_fields = ['account__code', 'account__name']
    readonly_fields = ['updated_at']
    date_hierarchy = 'balance_date'

