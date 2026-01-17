"""Tests for journal app serializers."""

from decimal import Decimal

from django.test import TestCase

from src.accounts.models import Account
from src.journal.models import (
    JournalEntry,
    JournalEntryLine,
    TransactionIdempotencyCache,
)
from src.journal.serializers import (
    JournalEntryCreateSerializer,
    JournalEntryLineCreateUpdateSerializer,
    JournalEntryReverseSerializer,
    JournalEntrySerializer,
)


class JournalEntryLineSerializerTests(TestCase):
    """Test suite for JournalEntryLineCreateUpdateSerializer."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.account = Account.objects.create(
            code='1110',
            name='Cash',
            account_type='ASSET',
            currency='KES',
            debit_or_credit='DR',
        )

    def test_valid_line_serialization(self):
        """Test valid line entry serialization."""
        data = {
            'account_code': '1110',
            'entry_type': 'DR',
            'amount': Decimal('1000.00'),
            'description': 'Cash receipt',
        }

        serializer = JournalEntryLineCreateUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            serializer.validated_data['amount'], Decimal('1000.00')
        )

    def test_invalid_entry_type(self):
        """Test invalid entry type validation."""
        data = {
            'account_code': '1110',
            'entry_type': 'INVALID',
            'amount': Decimal('1000.00'),
        }

        serializer = JournalEntryLineCreateUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('entry_type', serializer.errors)

    def test_zero_amount_validation(self):
        """Test that zero amount is rejected."""
        data = {
            'account_code': '1110',
            'entry_type': 'DR',
            'amount': Decimal('0.00'),
        }

        serializer = JournalEntryLineCreateUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_negative_amount_validation(self):
        """Test that negative amount is rejected."""
        data = {
            'account_code': '1110',
            'entry_type': 'DR',
            'amount': Decimal('-100.00'),
        }

        serializer = JournalEntryLineCreateUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)


class JournalEntryCreateSerializerTests(TestCase):
    """Test suite for JournalEntryCreateSerializer."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.cash_account = Account.objects.create(
            code='1110',
            name='Cash',
            account_type='ASSET',
            currency='KES',
            debit_or_credit='DR',
        )

        cls.loans_account = Account.objects.create(
            code='1210',
            name='Loans Receivable',
            account_type='ASSET',
            currency='KES',
            debit_or_credit='DR',
        )

    def test_valid_journal_entry_creation(self):
        """Test creating a valid journal entry."""
        data = {
            'idempotency_key': 'je-001',
            'description': 'Loan disbursement',
            'lines': [
                {
                    'account_code': '1210',
                    'entry_type': 'DR',
                    'amount': '10000.00',
                    'description': 'Loan principal',
                },
                {
                    'account_code': '1110',
                    'entry_type': 'CR',
                    'amount': '10000.00',
                    'description': 'Cash out',
                },
            ],
        }

        serializer = JournalEntryCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        je = serializer.save()
        self.assertEqual(je.status, 'POSTED')
        self.assertEqual(je.lines.count(), 2)

    def test_duplicate_idempotency_key(self):
        """Test that duplicate idempotency keys are rejected."""
        idempotency_key = 'je-dup-001'

        TransactionIdempotencyCache.objects.create(
            idempotency_key=idempotency_key
        )

        data = {
            'idempotency_key': idempotency_key,
            'description': 'Duplicate entry',
            'lines': [
                {
                    'account_code': '1210',
                    'entry_type': 'DR',
                    'amount': '1000.00',
                },
                {
                    'account_code': '1110',
                    'entry_type': 'CR',
                    'amount': '1000.00',
                },
            ],
        }

        serializer = JournalEntryCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('idempotency_key', serializer.errors)

    def test_unbalanced_entries_validation(self):
        """Test that unbalanced entries are rejected."""
        data = {
            'idempotency_key': 'je-unbal-001',
            'description': 'Unbalanced entry',
            'lines': [
                {
                    'account_code': '1210',
                    'entry_type': 'DR',
                    'amount': '10000.00',
                },
                {
                    'account_code': '1110',
                    'entry_type': 'CR',
                    'amount': '5000.00',
                },
            ],
        }

        serializer = JournalEntryCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_no_lines_validation(self):
        """Test that entry with no lines is rejected."""
        data = {
            'idempotency_key': 'je-nolines-001',
            'description': 'No lines entry',
            'lines': [],
        }

        serializer = JournalEntryCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('lines', serializer.errors)

    def test_single_line_validation(self):
        """Test that entry with single line is rejected."""
        data = {
            'idempotency_key': 'je-single-001',
            'description': 'Single line',
            'lines': [
                {
                    'account_code': '1210',
                    'entry_type': 'DR',
                    'amount': '1000.00',
                }
            ],
        }

        serializer = JournalEntryCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('lines', serializer.errors)

    def test_invalid_account_code(self):
        """Test that invalid account codes are rejected."""
        data = {
            'idempotency_key': 'je-invalid-acc-001',
            'description': 'Invalid account',
            'lines': [
                {
                    'account_code': '9999',
                    'entry_type': 'DR',
                    'amount': '1000.00',
                },
                {
                    'account_code': '1110',
                    'entry_type': 'CR',
                    'amount': '1000.00',
                },
            ],
        }

        serializer = JournalEntryCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_multi_line_balanced_entry(self):
        """Test creating entry with multiple balanced lines."""
        _fee_account = Account.objects.create(
            code='4210',
            name='Fee Income',
            account_type='INCOME',
            currency='KES',
            debit_or_credit='CR',
        )

        data = {
            'idempotency_key': 'je-multiline-001',
            'description': 'Loan with fee',
            'lines': [
                {
                    'account_code': '1210',
                    'entry_type': 'DR',
                    'amount': '10000.00',
                },
                {
                    'account_code': '1110',
                    'entry_type': 'CR',
                    'amount': '9900.00',
                },
                {
                    'account_code': '4210',
                    'entry_type': 'CR',
                    'amount': '100.00',
                },
            ],
        }

        serializer = JournalEntryCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        je = serializer.save()
        self.assertEqual(je.lines.count(), 3)


class JournalEntrySerializerTests(TestCase):
    """Test suite for JournalEntrySerializer (read-only)."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.account = Account.objects.create(
            code='1110',
            name='Cash',
            account_type='ASSET',
            currency='KES',
            debit_or_credit='DR',
        )

        cls.je = JournalEntry.objects.create(
            idempotency_key='je-read-001',
            description='Test read serializer',
            status='POSTED',
        )

        JournalEntryLine.objects.create(
            journal_entry=cls.je,
            account=cls.account,
            entry_type='DR',
            amount=Decimal('1000.00'),
        )

    def test_read_journal_entry(self):
        """Test reading a journal entry."""
        serializer = JournalEntrySerializer(self.je)
        data = serializer.data

        self.assertEqual(data['idempotency_key'], 'je-read-001')
        self.assertEqual(data['description'], 'Test read serializer')
        self.assertEqual(data['status'], 'POSTED')
        self.assertTrue(data['is_balanced'])
        self.assertEqual(len(data['lines']), 1)
        self.assertEqual(float(data['total_debit']), 1000.00)
        self.assertEqual(float(data['total_credit']), 0.0)


class JournalEntryReverseSerializerTests(TestCase):
    """Test suite for JournalEntryReverseSerializer."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.cash = Account.objects.create(
            code='1110',
            name='Cash',
            account_type='ASSET',
            currency='KES',
            debit_or_credit='DR',
        )

        cls.loans = Account.objects.create(
            code='1210',
            name='Loans Receivable',
            account_type='ASSET',
            currency='KES',
            debit_or_credit='DR',
        )

    def test_reverse_journal_entry(self):
        """Test reversing a journal entry."""
        je = JournalEntry.objects.create(
            idempotency_key='je-orig-001',
            description='Original entry',
            status='POSTED',
        )

        JournalEntryLine.objects.create(
            journal_entry=je,
            account=self.loans,
            entry_type='DR',
            amount=Decimal('5000.00'),
        )

        JournalEntryLine.objects.create(
            journal_entry=je,
            account=self.cash,
            entry_type='CR',
            amount=Decimal('5000.00'),
        )

        data = {
            'idempotency_key': 'je-rev-001',
            'description': 'Reversing original',
        }

        serializer = JournalEntryReverseSerializer(
            data=data, context={'journal_entry': je}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        reversed_entry = serializer.save()
        self.assertEqual(reversed_entry.status, 'POSTED')
        self.assertIsNotNone(reversed_entry.description)

    def test_reverse_non_posted_entry(self):
        """Test that non-posted entries cannot be reversed."""
        je = JournalEntry.objects.create(
            idempotency_key='je-pending-001',
            description='Pending entry',
            status='PENDING',
        )

        data = {'idempotency_key': 'je-rev-pending-001'}

        serializer = JournalEntryReverseSerializer(
            data=data, context={'journal_entry': je}
        )
        self.assertFalse(serializer.is_valid())

    def test_reverse_already_reversed_entry(self):
        """Test that reversed entries cannot be reversed again."""
        je1 = JournalEntry.objects.create(
            idempotency_key='je-orig-rev-001',
            description='Original',
            status='POSTED',
        )

        je2 = JournalEntry.objects.create(
            idempotency_key='je-rev-je1-001',
            description='Reversal of je1',
            status='POSTED',
            reversed_by=None,
        )

        je1.status = 'REVERSED'
        je1.reversed_by = je2
        je1.save()

        data = {'idempotency_key': 'je-rev-again-001'}

        serializer = JournalEntryReverseSerializer(
            data=data, context={'journal_entry': je1}
        )
        self.assertFalse(serializer.is_valid())
