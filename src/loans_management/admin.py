"""Admin registration for loans management."""

from django.contrib import admin

from .models import Borrower, Lender, Loan, LoanEvent, LoanRepayment


@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone_number', 'email', 'created_at']
    search_fields = ['full_name', 'phone_number', 'email', 'id_number']
    ordering = ['-created_at']


@admin.register(Lender)
class LenderAdmin(admin.ModelAdmin):
    list_display = ['name', 'capital_account_code', 'created_at']
    search_fields = ['name']
    ordering = ['-created_at']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'borrower',
        'lender',
        'principal_amount',
        'status',
        'currency',
        'created_at',
    ]
    list_filter = ['status', 'currency', 'lender']
    search_fields = ['id', 'borrower__full_name']
    readonly_fields = [
        'created_at',
        'updated_at',
        'disbursed_at',
        'outstanding_principal',
        'accrued_interest',
        'version',
    ]
    ordering = ['-created_at']


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'loan',
        'amount',
        'principal_component',
        'interest_component',
        'status',
        'paid_at',
    ]
    list_filter = ['status', 'paid_at']
    search_fields = ['loan__id', 'idempotency_key', 'external_reference']
    ordering = ['-paid_at']


@admin.register(LoanEvent)
class LoanEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'loan', 'event_type', 'idempotency_key', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['loan__id', 'idempotency_key']
    ordering = ['-created_at']
