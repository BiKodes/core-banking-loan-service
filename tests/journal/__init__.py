"""Tests for journal app models."""

from django.test import TestCase
from django.utils import timezone
from decimal import Decimal

from src.accounts.models import Account
from src.journal.models import JournalEntry, JournalEntryLine, TransactionIdempotencyCache


class JournalEntryModelTests(TestCase):
    """Test suite for JournalEntry model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests."""
        cls.cash_account = Account.objects.create(
            code='1110',
            name='Cash Account',
            account_type='ASSET',
            currency='KES',
            debit_or_credit='DR'
        )

        cls.loans_receivable = Account.objects.create(
            code='1210',
            name='Loans Receivable',
            account_type='ASSET',
            currency='KES',
            debit_or_credit='DR'
        )

        cls.fee_income = Account.objects.create(
            code='4210',
            name='Loan Origination Fee Income',
            account_type='INCOME',
            currency='KES',
            debit_or_credit='CR'
        )

    def test_create_journal_entry(self):
        """Test creating a simple journal entry."""
        je = JournalEntry.objects.create(
            idempotency_key='test-entry-001',
            description='Test journal entry',
            status='POSTED'
        )

        self.assertEqual(je.status, 'POSTED')
        self.assertEqual(je.idempotency_key, 'test-entry-001')
        self.assertIsNotNone(je.created_at)
        self.assertIsNotNone(je.updated_at)

    def test_journal_entry_with_balanced_lines(self):
        """Test journal entry with balanced debit and credit entries."""
        je = JournalEntry.objects.create(
            idempotency_key='test-balanced-001',
            description='Loan disbursement',
            status='POSTED'
        )

        JournalEntryLine.objects.create(
            journal_entry=je,
            account=self.loans_receivable,
            entry_type='DR',
            amount=Decimal('10000.00'),
            description='Loan disbursement principal'
        )

        JournalEntryLine.objects.create(
            journal_entry=je,
            account=self.cash_account,
            entry_type='CR',
            amount=Decimal('10000.00'),
            description='Cash out'
        )

        self.assertTrue(je.is_balanced())
        self.assertEqual(je.lines.count(), 2)

    def test_journal_entry_unbalanced_lines(self):
        """Test journal entry with unbalanced entries."""
        je = JournalEntry.objects.create(
            idempotency_key='test-unbalanced-001',
            description='Unbalanced entry',
            status='PENDING'
        )

        JournalEntryLine.objects.create(
            journal_entry=je,
            account=self.loans_receivable,
            entry_type='DR',
            amount=Decimal('10000.00')
        )

        JournalEntryLine.objects.create(
            journal_entry=je,
            account=self.cash_account,
            entry_type='CR',
            amount=Decimal('5000.00')
        )

        self.assertFalse(je.is_balanced())

    def test_journal_entry_reverse(self):
        """Test reversing a journal entry."""
        je = JournalEntry.objects.create(
            idempotency_key='test-reverse-001',
            description='Original loan disbursement',
            status='POSTED'
        )

        JournalEntryLine.objects.create(
            journal_entry=je,
            account=self.loans_receivable,
            entry_type='DR',
            amount=Decimal('10000.00')
        )

        JournalEntryLine.objects.create(
            journal_entry=je,
            account=self.cash_account,
            entry_type='CR',
            amount=Decimal('10000.00')
        )

        reversed_entry = je.reverse(
            idempotency_key='test-reverse-001-reversal',
            description='Reversal of original'
        )

        je.refresh_from_db()
        self.assertEqual(je.status, 'REVERSED')
        self.assertEqual(je.reversed_by, reversed_entry)

        self.assertEqual(reversed_entry.status, 'POSTED')
        self.assertEqual(reversed_entry.lines.count(), 2)

        dr_line = reversed_entry.lines.filter(entry_type='DR').first()
        cr_line = reversed_entry.lines.filter(entry_type='CR').first()

        self.assertEqual(dr_line.account, self.cash_account)
        self.assertEqual(cr_line.account, self.loans_receivable)

    def test_journal_entry_get_total(self):
        """Test getting total debits and credits."""
        je = JournalEntry.objects.create(
            idempotency_key='test-total-001',
            description='Multi-line entry',
            status='POSTED'
        )

        JournalEntryLine.objects.create(
            journal_entry=je,
            account=self.loans_receivable,
            entry_type='DR',
            amount=Decimal('5000.00')
        )

        JournalEntryLine.objects.create(
            journal_entry=je,
            account=self.cash_account,
            entry_type='DR',
            amount=Decimal('3000.00')
        )

        JournalEntryLine.objects.create(
            journal_entry=je,
            account=self.fee_income,
            entry_type='CR',
            amount=Decimal('8000.00')
        )

        total_dr = je.get_total('DR')
        total_cr = je.get_total('CR')

        self.assertEqual(total_dr, Decimal('8000.00'))
        self.assertEqual(total_cr, Decimal('8000.00'))


class JournalEntryLineModelTests(TestCase):
    """Test suite for JournalEntryLine model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests."""
        cls.je = JournalEntry.objects.create(
            idempotency_key='test-line-001',
            description='Test entry for lines',
            status='POSTED'
        )

        cls.account = Account.objects.create(
            code='1110',
            name='Cash',
            account_type='ASSET',
            currency='KES',
            debit_or_credit='DR'
        )

    def test_create_journal_entry_line(self):
        """Test creating a journal entry line."""
        line = JournalEntryLine.objects.create(
            journal_entry=self.je,
            account=self.account,
            entry_type='DR',
            amount=Decimal('1000.00'),
            description='Cash receipt'
        )

        self.assertEqual(line.entry_type, 'DR')
        self.assertEqual(line.amount, Decimal('1000.00'))
        self.assertEqual(line.account, self.account)
        self.assertEqual(line.journal_entry, self.je)

    def test_journal_entry_line_entry_type_choices(self):
        """Test that entry type is limited to DR or CR."""
        from django.core.exceptions import ValidationError

        line = JournalEntryLine(
            journal_entry=self.je,
            account=self.account,
            entry_type='INVALID',
            amount=Decimal('100.00')
        )

        with self.assertRaises(ValidationError):
            line.full_clean()


class TransactionIdempotencyCacheTests(TestCase):
    """Test suite for TransactionIdempotencyCache."""

    def test_create_idempotency_cache(self):
        """Test creating an idempotency cache record."""
        cache = TransactionIdempotencyCache.objects.create(
            idempotency_key='unique-key-123'
        )

        self.assertEqual(cache.idempotency_key, 'unique-key-123')
        self.assertIsNotNone(cache.created_at)

    def test_idempotency_key_uniqueness(self):
        """Test that idempotency keys must be unique."""
        from django.db import IntegrityError

        idempotency_key = 'duplicate-key-456'

        TransactionIdempotencyCache.objects.create(
            idempotency_key=idempotency_key
        )

        with self.assertRaises(IntegrityError):
            TransactionIdempotencyCache.objects.create(
                idempotency_key=idempotency_key
            )

    def test_prevents_duplicate_transactions(self):
        """Test that idempotency cache prevents duplicate processing."""
        idempotency_key = 'prevent-dup-789'

        cache1 = TransactionIdempotencyCache.objects.create(
            idempotency_key=idempotency_key
        )

        exists = TransactionIdempotencyCache.objects.filter(
            idempotency_key=idempotency_key
        ).exists()

        self.assertTrue(exists)
        self.assertEqual(
            TransactionIdempotencyCache.objects.filter(
                idempotency_key=idempotency_key
            ).count(),
            1
        )
