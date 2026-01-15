"""Serializers for loan management."""

from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers

from src.accounts.posting_rules.factory import PostingRuleFactory
from src.journal.models import JournalEntry
from .models import Borrower, Lender, Loan, LoanRepayment, LoanEvent


class BorrowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrower
        fields = ['id', 'full_name', 'phone_number', 'email', 'id_number', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class LenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lender
        fields = ['id', 'name', 'capital_account_code', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class LoanSerializer(serializers.ModelSerializer):
    borrower = BorrowerSerializer(read_only=True)
    lender = LenderSerializer(read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id', 'borrower', 'lender', 'principal_amount', 'currency', 'interest_rate',
            'term_months', 'origination_fee', 'status', 'disbursed_at', 'due_date',
            'maturity_date', 'outstanding_principal', 'accrued_interest', 'version',
            'loans_receivable_code', 'cash_account_code', 'fee_receivable_code', 'fee_income_code',
            'interest_income_code', 'interest_receivable_code', 'bad_debt_expense_code',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['status', 'disbursed_at', 'outstanding_principal', 'accrued_interest', 'created_at', 'updated_at', 'version']


class LoanCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = [
            'borrower', 'lender', 'principal_amount', 'currency', 'interest_rate',
            'term_months', 'origination_fee', 'due_date', 'maturity_date',
            'loans_receivable_code', 'cash_account_code', 'fee_receivable_code', 'fee_income_code',
            'interest_income_code', 'interest_receivable_code', 'bad_debt_expense_code'
        ]


class LoanDisbursementSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=100, required=False)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    origination_fee = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, default=Decimal('0.00'))

    def validate(self, data):
        loan: Loan = self.context['loan']
        if loan.status not in ['APPROVED', 'PENDING']:
            raise serializers.ValidationError('Loan is not in a disbursable state.')
        return data

    def save(self, **kwargs):
        loan: Loan = self.context['loan']
        idempotency_key = self.validated_data.get('idempotency_key') or f"loan-disbursement-{loan.id}"
        amount = Decimal(self.validated_data['amount'])
        origination_fee = Decimal(self.validated_data.get('origination_fee', Decimal('0.00')))

        event_payload = {
            'context': {
                'loan_id': str(loan.id),
                'amount': amount,
                'origination_fee': origination_fee,
                'loans_receivable_code': loan.loans_receivable_code,
                'cash_account_code': loan.cash_account_code,
                'fee_receivable_code': loan.fee_receivable_code,
                'fee_income_code': loan.fee_income_code,
            }
        }

        journal_entry = PostingRuleFactory.process_event('loan.disbursed', event_payload)

        loan.status = 'ACTIVE'
        loan.disbursed_at = timezone.now()
        loan.outstanding_principal = amount
        loan.save()

        LoanEvent.objects.create(
            loan=loan,
            event_type='DISBURSEMENT',
            idempotency_key=idempotency_key,
            journal_entry=journal_entry,
            payload=event_payload
        )

        return loan


class LoanRepaymentSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=100)
    principal_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    interest_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    external_reference = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, data):
        loan: Loan = self.context['loan']
        if loan.status not in ['ACTIVE', 'DISBURSED']:
            raise serializers.ValidationError('Loan is not active.')
        total = data['principal_amount'] + data['interest_amount']
        if total <= 0:
            raise serializers.ValidationError('Repayment amount must be greater than zero.')
        return data

    def save(self, **kwargs):
        loan: Loan = self.context['loan']
        idempotency_key = self.validated_data['idempotency_key']
        principal = Decimal(self.validated_data['principal_amount'])
        interest = Decimal(self.validated_data['interest_amount'])
        total = principal + interest

        repayment = LoanRepayment.objects.create(
            loan=loan,
            idempotency_key=idempotency_key,
            amount=total,
            principal_component=principal,
            interest_component=interest,
            external_reference=self.validated_data.get('external_reference', '')
        )

        event_payload = {
            'context': {
                'loan_id': str(loan.id),
                'principal_amount': principal,
                'interest_amount': interest,
                'cash_account_code': loan.cash_account_code,
                'loans_receivable_code': loan.loans_receivable_code,
                'interest_income_code': loan.interest_income_code,
                'repayment_id': repayment.id,
            }
        }

        journal_entry = PostingRuleFactory.process_event('loan.repayment_received', event_payload)

        loan.update_outstanding(principal_delta=-principal)
        loan.accrued_interest = loan.accrued_interest - interest if loan.accrued_interest else Decimal('0.00')
        if loan.outstanding_principal <= 0:
            loan.status = 'REPAID'
        loan.save()

        repayment.status = 'POSTED'
        repayment.save()

        LoanEvent.objects.create(
            loan=loan,
            event_type='REPAYMENT',
            idempotency_key=idempotency_key,
            journal_entry=journal_entry,
            payload=event_payload
        )

        return repayment


class LoanWriteOffSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=100)
    write_off_amount = serializers.DecimalField(max_digits=14, decimal_places=2)

    def validate(self, data):
        loan: Loan = self.context['loan']
        if loan.status not in ['ACTIVE', 'DEFAULTED']:
            raise serializers.ValidationError('Loan must be active or defaulted to write off.')
        if data['write_off_amount'] <= 0:
            raise serializers.ValidationError('Write-off amount must be greater than zero.')
        return data

    def save(self, **kwargs):
        loan: Loan = self.context['loan']
        amount = Decimal(self.validated_data['write_off_amount'])
        idempotency_key = self.validated_data['idempotency_key']

        event_payload = {
            'context': {
                'loan_id': str(loan.id),
                'write_off_amount': amount,
                'bad_debt_expense_code': loan.bad_debt_expense_code,
                'loans_receivable_code': loan.loans_receivable_code,
            }
        }

        journal_entry = PostingRuleFactory.process_event('loan.written_off', event_payload)

        loan.update_outstanding(principal_delta=-amount)
        loan.status = 'WRITTEN_OFF'
        loan.save()

        LoanEvent.objects.create(
            loan=loan,
            event_type='WRITE_OFF',
            idempotency_key=idempotency_key,
            journal_entry=journal_entry,
            payload=event_payload
        )
        return loan


class LoanInterestAccrualSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=100)
    accrued_interest = serializers.DecimalField(max_digits=14, decimal_places=2)
    accrual_date = serializers.DateField(required=False)

    def validate(self, data):
        loan: Loan = self.context['loan']
        if loan.status not in ['ACTIVE', 'DISBURSED']:
            raise serializers.ValidationError('Loan must be active to accrue interest.')
        if data['accrued_interest'] <= 0:
            raise serializers.ValidationError('Accrued interest must be positive.')
        return data

    def save(self, **kwargs):
        loan: Loan = self.context['loan']
        amount = Decimal(self.validated_data['accrued_interest'])
        accrual_date = self.validated_data.get('accrual_date') or timezone.now().date()

        event_payload = {
            'context': {
                'loan_id': str(loan.id),
                'accrued_interest': amount,
                'accrual_date': accrual_date,
                'interest_receivable_code': loan.interest_receivable_code,
                'interest_income_code': loan.interest_income_code,
            }
        }

        journal_entry = PostingRuleFactory.process_event('loan.interest_accrued', event_payload)

        loan.update_outstanding(principal_delta=Decimal('0.00'), interest_delta=amount)
        loan.save()

        LoanEvent.objects.create(
            loan=loan,
            event_type='ACCRUAL',
            idempotency_key=self.validated_data['idempotency_key'],
            journal_entry=journal_entry,
            payload=event_payload
        )
        return loan


class LoanRepaymentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRepayment
        fields = [
            'id', 'loan', 'idempotency_key', 'amount', 'principal_component',
            'interest_component', 'paid_at', 'external_reference', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class LoanEventSerializer(serializers.ModelSerializer):
    journal_entry = serializers.PrimaryKeyRelatedField(queryset=JournalEntry.objects.all(), allow_null=True)

    class Meta:
        model = LoanEvent
        fields = ['id', 'loan', 'event_type', 'idempotency_key', 'journal_entry', 'payload', 'created_at']
        read_only_fields = fields
