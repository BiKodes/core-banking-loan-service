"""Integration tests for loan lifecycle and accounting posting."""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from src.accounts.models import Account
from src.journal.models import JournalEntry
from src.loans_management.models import Borrower, Lender, Loan
from src.loans_management.serializers import (
    LoanDisbursementSerializer,
    LoanRepaymentSerializer,
    LoanWriteOffSerializer,
    LoanInterestAccrualSerializer,
)


class LoanLifecyclePostingTests(TestCase):
    """Ensure loan operations create correct journal entries and update balances."""

    def setUp(self):
        self.cash = Account.objects.create(code='1110', name='Cash', account_type='ASSET')
        self.loan_principal = Account.objects.create(code='1210', name='Loan Principal', account_type='ASSET')
        self.fee_receivable = Account.objects.create(code='1220', name='Fee Receivable', account_type='ASSET')
        self.interest_income = Account.objects.create(code='4100', name='Interest Income', account_type='INCOME')
        self.fee_income = Account.objects.create(code='4210', name='Fee Income', account_type='INCOME')
        self.bad_debt = Account.objects.create(code='5100', name='Bad Debt Expense', account_type='EXPENSE')

        self.borrower = Borrower.objects.create(full_name='Test Borrower')
        self.lender = Lender.objects.create(name='Test Lender')
        self.loan = Loan.objects.create(
            borrower=self.borrower,
            lender=self.lender,
            principal_amount=Decimal('10000.00'),
            currency='KES',
            interest_rate=Decimal('12.00'),
            term_months=12,
            origination_fee=Decimal('500.00'),
            status='APPROVED',
            loans_receivable_code='1210',
            cash_account_code='1110',
            fee_receivable_code='1220',
            fee_income_code='4210',
            interest_income_code='4100',
            interest_receivable_code='1220',
            bad_debt_expense_code='5100',
        )

    def test_disbursement_posts_entries(self):
        serializer = LoanDisbursementSerializer(
            data={'amount': '10000.00', 'origination_fee': '500.00'},
            context={'loan': self.loan},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, 'ACTIVE')
        self.assertEqual(self.loan.outstanding_principal, Decimal('10000.00'))

        self.assertGreaterEqual(JournalEntry.objects.count(), 2)
        principal_entry = JournalEntry.objects.filter(idempotency_key__startswith='loan-disbursement').first()
        self.assertIsNotNone(principal_entry)
        self.assertTrue(principal_entry.is_balanced())

    def test_repayment_posts_entries_and_reduces_outstanding(self):
        serializer = LoanDisbursementSerializer(data={'amount': '10000.00'}, context={'loan': self.loan})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        repay = LoanRepaymentSerializer(
            data={'idempotency_key': 'repay-1', 'principal_amount': '1000.00', 'interest_amount': '200.00'},
            context={'loan': self.loan},
        )
        self.assertTrue(repay.is_valid(), repay.errors)
        repayment_obj = repay.save()

        self.loan.refresh_from_db()
        self.assertEqual(self.loan.outstanding_principal, Decimal('9000.00'))
        self.assertEqual(repayment_obj.status, 'POSTED')
        self.assertGreaterEqual(JournalEntry.objects.filter(idempotency_key__startswith='loan-repayment').count(), 1)

    def test_writeoff_posts_entries(self):
        serializer = LoanDisbursementSerializer(data={'amount': '5000.00'}, context={'loan': self.loan})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        writeoff = LoanWriteOffSerializer(
            data={'idempotency_key': 'writeoff-1', 'write_off_amount': '5000.00'},
            context={'loan': self.loan},
        )
        self.assertTrue(writeoff.is_valid(), writeoff.errors)
        writeoff.save()
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, 'WRITTEN_OFF')

    def test_interest_accrual_posts_entries(self):
        serializer = LoanDisbursementSerializer(data={'amount': '10000.00'}, context={'loan': self.loan})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        accrual = LoanInterestAccrualSerializer(
            data={'idempotency_key': 'accrual-1', 'accrued_interest': '300.00', 'accrual_date': timezone.now().date()},
            context={'loan': self.loan},
        )
        self.assertTrue(accrual.is_valid(), accrual.errors)
        accrual.save()
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.accrued_interest, Decimal('300.00'))