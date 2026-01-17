"""
Journal Entry Models for Core Banking Loan Service.

Handles all journal entry and transaction posting logic.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from src.accounts.models import DEBIT_CREDIT_TYPES, TRANSACTION_STATUS, Account
from src.common.models import TenantAwareModel


class JournalEntry(TenantAwareModel):
    """
    Journal Entry model.

    Represents a complete double-entry transaction in the general ledger.
    """

    idempotency_key = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Unique key for idempotent transaction processing",
    )
    description = models.TextField(help_text="Transaction description")

    status = models.CharField(
        max_length=20,
        choices=TRANSACTION_STATUS,
        default="POSTED",
        db_index=True,
        help_text="Transaction status",
    )

    reversed_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reverses',
        help_text="Reference to reversing transaction if this was reversed",
    )

    posted_at = models.DateTimeField(
        null=True, blank=True, help_text="When the transaction was posted"
    )
    created_by = models.CharField(
        max_length=255, blank=True, help_text="User who created the transaction"
    )

    version = models.IntegerField(
        default=0, help_text="Optimistic locking version number"
    )

    class Meta:
        db_table = 'journal_journalentry'
        ordering = ['-created_at']
        unique_together = [('organization', 'idempotency_key')]
        indexes = [
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.idempotency_key} - {self.description[:50]}"

    @transaction.atomic
    def save(self, *args, **kwargs):
        """Save transaction with validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate transaction integrity."""
        debit_total = self.entries.filter(entry_type="DR").aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        credit_total = self.entries.filter(entry_type="CR").aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        if debit_total != credit_total:
            raise ValidationError(
                f"Transaction does not balance. "
                f"Debits: {debit_total}, Credits: {credit_total}"
            )

    def get_total(self):
        """Get transaction total amount."""
        return self.entries.filter(entry_type="DR").aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

    def is_balanced(self):
        """Check if transaction is balanced."""
        debit_total = self.entries.filter(entry_type="DR").aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        credit_total = self.entries.filter(entry_type="CR").aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        return debit_total == credit_total

    def reverse(self):
        """
        Create a reversing journal entry for this transaction.
        """
        if self.status == "REVERSED":
            raise ValidationError("Transaction already reversed.")

        reversing_entry = JournalEntry.objects.create(
            idempotency_key=f"{self.idempotency_key}-REVERSED-{timezone.now().timestamp()}",
            description=f"Reversal of: {self.description}",
            status="POSTED",
            created_by=self.created_by,
        )

        for entry in self.entries.all():
            new_entry_type = "CR" if entry.entry_type == "DR" else "DR"
            JournalEntryLine.objects.create(
                journal_entry=reversing_entry,
                account=entry.account,
                entry_type=new_entry_type,
                amount=entry.amount,
                description=f"Reversal of: {entry.description}",
            )

        self.status = "REVERSED"
        self.reversed_by = reversing_entry
        self.save()

        return reversing_entry


class JournalEntryLine(models.Model):
    """
    Journal Entry Line Item.

    Individual debit or credit line within a journal entry.
    Multiple lines can be part of a single JournalEntry.
    """

    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='entries',
        help_text="Parent journal entry",
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='journal_entries',
        help_text="Account for this entry line",
    )

    entry_type = models.CharField(
        max_length=2, choices=DEBIT_CREDIT_TYPES, help_text="Debit or Credit"
    )

    amount = models.DecimalField(
        max_digits=15, decimal_places=2, help_text="Entry amount"
    )

    description = models.TextField(
        blank=True, help_text="Line-specific description"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'journal_journalentryline'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['journal_entry']),
            models.Index(fields=['account']),
        ]

    def __str__(self):
        return f"{self.account.code} {self.entry_type} {self.amount}"

    def clean(self):
        """Validate entry line."""
        if self.amount <= 0:
            raise ValidationError("Amount must be greater than zero.")

        if self.account.is_control_account:
            raise ValidationError("Cannot make entries into control accounts.")


class TransactionIdempotencyCache(TenantAwareModel):
    """
    Cache for idempotent transactions.

    Stores the result of processed transactions to return on duplicate requests.
    Prevents duplicate processing when same idempotency_key is submitted.
    """

    idempotency_key = models.CharField(
        max_length=255,
        db_index=True,
    )

    journal_entry = models.OneToOneField(
        JournalEntry,
        on_delete=models.CASCADE,
        help_text="The successfully processed transaction",
    )

    request_hash = models.CharField(
        max_length=255, help_text="Hash of original request for validation"
    )

    class Meta:
        db_table = 'journal_idempotency_cache'
        unique_together = [('organization', 'idempotency_key')]

    def __str__(self):
        return f"Cache: {self.idempotency_key}"
