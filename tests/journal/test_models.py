"""Tests for journal app models."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from src.accounts.models import Account
from src.journal.models import JournalEntry, JournalEntryLine


class JournalEntryTests(TestCase):
    """Test JournalEntry model."""

    def setUp(self):
        """Set up accounts for journal entry tests."""
        self.asset = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET'
        )
        self.liability = Account.objects.create(
            code='2000', name='Loan Payable', account_type='LIABILITY'
        )

    def test_journal_entry_creation(self):
        """Ensure journal entry can be created with POSTED status."""
        entry = JournalEntry.objects.create(
            idempotency_key='test-001',
            description='Test transaction',
            status='POSTED',
        )
        self.assertEqual(entry.status, 'POSTED')

    def test_balance_validation(self):
        """Unbalanced entries should fail validation."""
        entry = JournalEntry.objects.create(
            idempotency_key='test-002',
            description='Unbalanced entry',
            status='POSTED',
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.asset,
            entry_type='DR',
            amount=Decimal('1000.00'),
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.liability,
            entry_type='CR',
            amount=Decimal('500.00'),
        )
        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_balanced_entry(self):
        """Balanced entries should pass validation and be marked balanced."""
        entry = JournalEntry.objects.create(
            idempotency_key='test-003',
            description='Balanced entry',
            status='POSTED',
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.asset,
            entry_type='DR',
            amount=Decimal('1000.00'),
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.liability,
            entry_type='CR',
            amount=Decimal('1000.00'),
        )
        entry.full_clean()
        self.assertTrue(entry.is_balanced())

    def test_transaction_reversal(self):
        """Reversing an entry should create offsetting lines."""
        entry = JournalEntry.objects.create(
            idempotency_key='test-004',
            description='Original entry',
            status='POSTED',
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.asset,
            entry_type='DR',
            amount=Decimal('1000.00'),
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.liability,
            entry_type='CR',
            amount=Decimal('1000.00'),
        )
        reversed_entry = entry.reverse()
        self.assertEqual(reversed_entry.status, 'POSTED')
        self.assertEqual(entry.status, 'REVERSED')
        self.assertEqual(entry.reversed_by, reversed_entry)
        reversing_lines = reversed_entry.entries.all()
        self.assertEqual(reversing_lines.count(), 2)
        asset_entry = reversing_lines.get(account=self.asset)
        self.assertEqual(asset_entry.entry_type, 'CR')


class JournalEntryLineTests(TestCase):
    """Test JournalEntryLine model."""

    def setUp(self):
        self.account = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET'
        )
        self.journal_entry = JournalEntry.objects.create(
            idempotency_key='test-005',
            description='Test entry',
            status='POSTED',
        )

    def test_entry_line_creation(self):
        line = JournalEntryLine.objects.create(
            journal_entry=self.journal_entry,
            account=self.account,
            entry_type='DR',
            amount=Decimal('1000.00'),
        )
        self.assertEqual(line.entry_type, 'DR')
        self.assertEqual(line.amount, Decimal('1000.00'))

    def test_prevent_negative_amount(self):
        line = JournalEntryLine(
            journal_entry=self.journal_entry,
            account=self.account,
            entry_type='DR',
            amount=Decimal('-500.00'),
        )
        with self.assertRaises(ValidationError):
            line.full_clean()

    def test_prevent_control_account_entry(self):
        control_account = Account.objects.create(
            code='CONTROL',
            name='Control Account',
            account_type='ASSET',
            is_control_account=True,
        )
        line = JournalEntryLine(
            journal_entry=self.journal_entry,
            account=control_account,
            entry_type='DR',
            amount=Decimal('1000.00'),
        )
        with self.assertRaises(ValidationError):
            line.full_clean()


class JournalIdempotencyTests(TestCase):
    """Tests for idempotency handling in JournalEntry."""

    def test_idempotency_key_uniqueness(self):
        JournalEntry.objects.create(
            idempotency_key='unique-001', description='First', status='POSTED'
        )
        with self.assertRaises(Exception):
            JournalEntry.objects.create(
                idempotency_key='unique-001',
                description='Duplicate',
                status='POSTED',
            )
