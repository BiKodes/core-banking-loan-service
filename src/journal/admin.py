"""Admin configuration for journal app."""

from django.contrib import admin
from .models import JournalEntry, JournalEntryLine, TransactionIdempotencyCache


class JournalEntryLineInline(admin.TabularInline):
    """Inline admin for JournalEntryLine."""

    model = JournalEntryLine
    extra = 0
    fields = ('account', 'entry_type', 'amount', 'description')
    readonly_fields = ('created_at',)
    ordering = ('id',)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    """Admin for JournalEntry."""

    list_display = ('id', 'idempotency_key', 'description', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('description', 'idempotency_key')
    readonly_fields = ('idempotency_key', 'created_at', 'updated_at', 'is_balanced_display')
    fields = (
        'idempotency_key', 'description', 'status',
        'reversed_by', 'is_balanced_display', 'created_at', 'updated_at'
    )
    inlines = [JournalEntryLineInline]
    ordering = ('-created_at',)

    def is_balanced_display(self, obj):
        """Display whether the journal entry is balanced."""
        return obj.is_balanced()

    is_balanced_display.short_description = 'Is Balanced'
    is_balanced_display.boolean = True

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of posted entries."""
        if obj and obj.status == 'POSTED':
            return False
        return True


@admin.register(JournalEntryLine)
class JournalEntryLineAdmin(admin.ModelAdmin):
    """Admin for JournalEntryLine."""

    list_display = ('id', 'journal_entry', 'account', 'entry_type', 'amount', 'created_at')
    list_filter = ('entry_type', 'created_at', 'account__account_type')
    search_fields = ('journal_entry__description', 'account__code', 'account__name')
    readonly_fields = ('journal_entry', 'created_at')
    fields = ('journal_entry', 'account', 'entry_type', 'amount', 'description', 'created_at')
    ordering = ('-journal_entry__created_at', 'id')

    def has_add_permission(self, request):
        """Prevent direct creation of lines (must create via JournalEntry)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of lines from posted entries."""
        if obj and obj.journal_entry.status == 'POSTED':
            return False
        return True


@admin.register(TransactionIdempotencyCache)
class TransactionIdempotencyCacheAdmin(admin.ModelAdmin):
    """Admin for TransactionIdempotencyCache."""

    list_display = ('id', 'idempotency_key', 'created_at')
    search_fields = ('idempotency_key',)
    readonly_fields = ('idempotency_key', 'created_at')
    fields = ('idempotency_key', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        """Prevent direct creation (created automatically)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion to maintain idempotency."""
        return False
