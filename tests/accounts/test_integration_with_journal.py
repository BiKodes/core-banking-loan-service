"""Integration tests between Accounts and Journal apps."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from src.accounts.models import Account
from src.journal.models import JournalEntry, JournalEntryLine


class AccountJournalIntegrationTests(TestCase):
    """Tests that involve account balances derived from journal entries."""

    def setUp(self):
        """Create base accounts for integration scenarios."""
        self.asset_control = Account.objects.create(
            code='1000',
            name='Current Assets',
            account_type='ASSET',
            is_control_account=True,
        )

        self.asset_cash = Account.objects.create(
            code='1100',
            name='Cash',
            account_type='ASSET',
            parent=self.asset_control,
        )

        self.income = Account.objects.create(
            code='4000', name='Interest Income', account_type='INCOME'
        )

    def _create_journal_entry(self):
        return JournalEntry.objects.create(
            idempotency_key=f'test-{timezone.now().timestamp()}',
            description='Test entry',
            status='POSTED',
        )

    def test_balance_calculation_asset(self):
        """Asset accounts compute balance as DR - CR."""
        JournalEntryLine.objects.create(
            journal_entry=self._create_journal_entry(),
            account=self.asset_cash,
            entry_type='DR',
            amount=Decimal('1000.00'),
        )
        JournalEntryLine.objects.create(
            journal_entry=self._create_journal_entry(),
            account=self.asset_cash,
            entry_type='CR',
            amount=Decimal('200.00'),
        )
        self.assertEqual(self.asset_cash.get_balance(), Decimal('800.00'))

    def test_balance_calculation_income(self):
        """Income accounts compute balance as CR - DR."""
        JournalEntryLine.objects.create(
            journal_entry=self._create_journal_entry(),
            account=self.income,
            entry_type='CR',
            amount=Decimal('500.00'),
        )
        JournalEntryLine.objects.create(
            journal_entry=self._create_journal_entry(),
            account=self.income,
            entry_type='DR',
            amount=Decimal('100.00'),
        )
        self.assertEqual(self.income.get_balance(), Decimal('400.00'))

    def test_prevent_deletion_with_entries(self):
        """Accounts with journal entries cannot be deleted."""
        JournalEntryLine.objects.create(
            journal_entry=self._create_journal_entry(),
            account=self.asset_cash,
            entry_type='DR',
            amount=Decimal('1000.00'),
        )
        with self.assertRaises(ValidationError):
            self.asset_cash.delete()
