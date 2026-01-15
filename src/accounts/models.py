"""
Core Banking Loan Service - Account Management Models
"""

from collections import OrderedDict
from decimal import Decimal
from datetime import datetime

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q, F, Sum

from src.common import TenantAwareModel


ACCOUNT_TYPES = (
    ("ASSET", "Asset"),
    ("LIABILITY", "Liability"),
    ("EQUITY", "Equity"),
    ("INCOME", "Income"),
    ("EXPENSE", "Expense"),
)

CURRENCY_CHOICES = (
    ("KES", "Kenyan Shilling"),
    ("UGX", "Ugandan Shilling"),
    ("USD", "United States Dollar"),
)

DEBIT_CREDIT_TYPES = (
    ("DR", "Debit"),
    ("CR", "Credit"),
)

TRANSACTION_STATUS = (
    ("PENDING", "Pending"),
    ("POSTED", "Posted"),
    ("REVERSED", "Reversed"),
    ("VOIDED", "Voided"),
)

def validate_account_identifiers(value):
    """Validate account identifiers are comma-separated valid strings."""
    if not value:
        return
    identifiers = [id.strip() for id in value.split(",")]
    for identifier in identifiers:
        if not identifier.isidentifier():
            raise ValidationError(
                f"Invalid identifier '{identifier}'. Must be alphanumeric with underscores."
            )

class AccountManager(models.Manager):
    """Custom manager for accounts with safety constraints."""

    def get_queryset(self):
        """Return queryset with related data."""
        return super().get_queryset().select_related('parent')

    def by_type(self, account_type):
        """Get accounts by type."""
        return self.filter(account_type=account_type)

    def assets(self):
        """Get all asset accounts."""
        return self.by_type("ASSET")

    def liabilities(self):
        """Get all liability accounts."""
        return self.by_type("LIABILITY")

    def equity(self):
        """Get all equity accounts."""
        return self.by_type("EQUITY")

    def income(self):
        """Get all income accounts."""
        return self.by_type("INCOME")

    def expenses(self):
        """Get all expense accounts."""
        return self.by_type("EXPENSE")

    def active(self):
        """Get all active accounts."""
        return self.filter(is_active=True)


class Account(TenantAwareModel):
    """
    Chart of Accounts model.

    Represents a general ledger account in the accounting system.
    Supports hierarchical account structures with parent-child relationships.
    """

    code = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Unique account identifier (e.g., 1000-CASH)"
    )
    name = models.CharField(
        max_length=255,
        help_text="Account name (e.g., M-Pesa Cash Account)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed account description"
    )

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPES,
        db_index=True,
        help_text="Type of account: ASSET, LIABILITY, EQUITY, INCOME, EXPENSE"
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="KES",
        help_text="Primary currency for this account"
    )

    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='children',
        help_text="Parent account for hierarchical structure"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether account is active and can be used"
    )
    is_control_account = models.BooleanField(
        default=False,
        help_text="Control accounts are parent accounts only (no transactions)"
    )
    is_system_account = models.BooleanField(
        default=False,
        help_text="System accounts cannot be modified or deleted"
    )

    identifiers = models.TextField(
        blank=True,
        validators=[validate_account_identifiers],
        help_text="Comma-separated custom identifiers for system tagging"
    )

    version = models.IntegerField(
        default=0,
        help_text="Optimistic locking version number"
    )

    objects = AccountManager()

    class Meta:
        db_table = 'accounts_account'
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['account_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['parent']),
        ]
        unique_together = [('organization', 'code', 'currency')]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        """Custom save with validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate account data."""
        if self.parent and not self.parent.is_control_account:
            raise ValidationError(
                "Parent account must be marked as control account."
            )

        if self.parent and self.is_control_account:
            current = self.parent
            while current:
                if current.id == self.id:
                    raise ValidationError("Circular account hierarchy detected.")
                current = current.parent

        if self.is_system_account and self.pk:
            original = Account.objects.get(pk=self.pk)
            if not original.is_system_account:
                raise ValidationError("Cannot convert account to system account.")

    def delete(self, *args, **kwargs):
        """Prevent deletion of accounts with transactions."""
        if self.is_system_account:
            raise ValidationError(
                f"Cannot delete system account '{self.name}'."
            )
        if self.entries.exists():
            raise ValidationError(
                f"Cannot delete account '{self.name}' with existing transactions."
            )
        super().delete(*args, **kwargs)


    def get_balance(self, as_of_date=None):
        """
        Get account balance as of a specific date.
        """
        if as_of_date is None:
            as_of_date = timezone.now()

        if self.is_control_account:
            balance = Decimal('0')
            for child in self.children.all():
                balance += child.get_balance(as_of_date)
            return balance

        entries = self.entries.filter(
            transaction__created_at__lte=as_of_date,
            transaction__status="POSTED"
        )

        debit_total = entries.filter(entry_type="DR").aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        credit_total = entries.filter(entry_type="CR").aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        if self.account_type in ["ASSET", "EXPENSE"]:
            return debit_total - credit_total
        else:
            return credit_total - debit_total

    def get_balance_at_date(self, as_of_date):
        """Alias for get_balance with explicit date parameter."""
        return self.get_balance(as_of_date)

    @property
    def current_balance(self):
        """Get current account balance."""
        return self.get_balance()

    @property
    def debit_total(self):
        """Get total debits for this account."""
        return self.entries.filter(
            entry_type="DR",
            transaction__status="POSTED"
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    @property
    def credit_total(self):
        """Get total credits for this account."""
        return self.entries.filter(
            entry_type="CR",
            transaction__status="POSTED"
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    def get_hierarchy_path(self):
        """Get full account hierarchy path as list."""
        path = [self]
        current = self.parent
        while current:
            path.insert(0, current)
            current = current.parent
        return path

    def get_hierarchy_string(self):
        """Get account hierarchy as formatted string."""
        path = self.get_hierarchy_path()
        return " > ".join([str(account) for account in path])


class AccountBalance(models.Model):
    """
    Materialized view for account balances.

    Caches account balances for performance.
    This is updated regularly (daily) for financial reporting.
    """

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='balance_snapshots'
    )

    balance_date = models.DateField(
        db_index=True,
        help_text="Date of balance snapshot"
    )

    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Account balance on this date"
    )

    debit_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total debits up to this date"
    )

    credit_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total credits up to this date"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_balance'
        ordering = ['-balance_date']
        indexes = [
            models.Index(fields=['account', 'balance_date']),
            models.Index(fields=['balance_date']),
        ]
        unique_together = [('account', 'balance_date')]

    def __str__(self):
        return f"{self.account.code} - {self.balance_date}: {self.balance}"
