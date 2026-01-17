"""Posting rules for loan operations."""

from decimal import Decimal

from django.db import transaction

from .base import PostingRuleBase


class LoanDisbursement(PostingRuleBase):
    """
    Generate accounting entries for loan disbursement.
    """

    @transaction.atomic
    def process(self, event):
        """
        Process a loan disbursement event.
        """
        context = event.get('context', {})
        loan_id = context.get('loan_id')
        amount = Decimal(str(context.get('amount', 0)))
        origination_fee = Decimal(str(context.get('origination_fee', 0)))

        principal_entries = [
            {
                'account_code': context.get('loans_receivable_code', '1210'),
                'entry_type': 'DR',
                'amount': amount,
                'description': f'Loan disbursement - Loan {loan_id}',
            },
            {
                'account_code': context.get('cash_account_code', '1110'),
                'entry_type': 'CR',
                'amount': amount,
                'description': f'Cash disbursed - Loan {loan_id}',
            },
        ]

        journal_entry = self.create_journal_entry(
            idempotency_key=f"loan-disbursement-{loan_id}",
            description=f"Loan disbursement for loan {loan_id}",
            entries_data=principal_entries,
        )

        if origination_fee > 0:
            fee_entries = [
                {
                    'account_code': context.get('fee_receivable_code', '1220'),
                    'entry_type': 'DR',
                    'amount': origination_fee,
                    'description': f'Loan origination fee receivable - Loan {loan_id}',
                },
                {
                    'account_code': context.get('fee_income_code', '4210'),
                    'entry_type': 'CR',
                    'amount': origination_fee,
                    'description': f'Fee income - Loan {loan_id}',
                },
            ]

            self.create_journal_entry(
                idempotency_key=f"loan-fee-{loan_id}",
                description=f"Loan origination fee - Loan {loan_id}",
                entries_data=fee_entries,
            )

        return journal_entry


class LoanRepayment(PostingRuleBase):
    """
    Generate accounting entries for loan repayment.
    """

    @transaction.atomic
    def process(self, event):
        """
        Process a loan repayment event.
        """
        context = event.get('context', {})
        loan_id = context.get('loan_id')
        principal = Decimal(str(context.get('principal_amount', 0)))
        interest = Decimal(str(context.get('interest_amount', 0)))
        total = principal + interest

        entries = [
            {
                'account_code': context.get('cash_account_code', '1110'),
                'entry_type': 'DR',
                'amount': total,
                'description': f'Loan repayment received - Loan {loan_id}',
            },
            {
                'account_code': context.get('loans_receivable_code', '1210'),
                'entry_type': 'CR',
                'amount': principal,
                'description': f'Principal repaid - Loan {loan_id}',
            },
            {
                'account_code': context.get('interest_income_code', '4100'),
                'entry_type': 'CR',
                'amount': interest,
                'description': f'Interest income - Loan {loan_id}',
            },
        ]

        return self.create_journal_entry(
            idempotency_key=f"loan-repayment-{loan_id}-{context.get('repayment_id')}",
            description=f"Loan repayment - Loan {loan_id}",
            entries_data=entries,
        )


class LoanWriteOff(PostingRuleBase):
    """
    Generate accounting entries for loan write-off.
    """

    @transaction.atomic
    def process(self, event):
        """
        Process a loan write-off event.
        """
        context = event.get('context', {})
        loan_id = context.get('loan_id')
        write_off_amount = Decimal(str(context.get('write_off_amount', 0)))

        entries = [
            {
                'account_code': context.get('bad_debt_expense_code', '5100'),
                'entry_type': 'DR',
                'amount': write_off_amount,
                'description': f'Bad debt expense - Loan {loan_id}',
            },
            {
                'account_code': context.get('loans_receivable_code', '1210'),
                'entry_type': 'CR',
                'amount': write_off_amount,
                'description': f'Loan write-off - Loan {loan_id}',
            },
        ]

        return self.create_journal_entry(
            idempotency_key=f"loan-writeoff-{loan_id}",
            description=f"Loan write-off - Loan {loan_id}",
            entries_data=entries,
        )


class LoanInterestAccrual(PostingRuleBase):
    """
    Generate accounting entries for interest accrual.
    """

    @transaction.atomic
    def process(self, event):
        """
        Process interest accrual event.
        """
        context = event.get('context', {})
        loan_id = context.get('loan_id')
        accrued_interest = Decimal(str(context.get('accrued_interest', 0)))

        entries = [
            {
                'account_code': context.get('interest_receivable_code', '1220'),
                'entry_type': 'DR',
                'amount': accrued_interest,
                'description': f'Interest receivable accrual - Loan {loan_id}',
            },
            {
                'account_code': context.get('interest_income_code', '4100'),
                'entry_type': 'CR',
                'amount': accrued_interest,
                'description': f'Interest income accrual - Loan {loan_id}',
            },
        ]

        return self.create_journal_entry(
            idempotency_key=f"interest-accrual-{loan_id}-{context.get('accrual_date')}",
            description=f"Interest accrual - Loan {loan_id}",
            entries_data=entries,
        )
