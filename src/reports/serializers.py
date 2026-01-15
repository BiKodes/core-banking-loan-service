"""Report serializers for financial reporting."""

from rest_framework import serializers
from decimal import Decimal


class AccountBalanceReportSerializer(serializers.Serializer):
    """Serializer for account balance report."""
    
    account_id = serializers.IntegerField()
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    account_type = serializers.CharField()
    currency = serializers.CharField()
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    debit_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    credit_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    as_of_date = serializers.DateTimeField()


class TransactionHistorySerializer(serializers.Serializer):
    """Serializer for transaction history with running balance."""
    
    transaction_id = serializers.IntegerField()
    date = serializers.DateTimeField()
    idempotency_key = serializers.CharField()
    description = serializers.CharField()
    entry_type = serializers.CharField()
    debit = serializers.DecimalField(max_digits=15, decimal_places=2)
    credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    running_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    status = serializers.CharField()


class TrialBalanceLineSerializer(serializers.Serializer):
    """Serializer for trial balance line item."""
    
    account_type = serializers.CharField()
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    debit_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    credit_balance = serializers.DecimalField(max_digits=15, decimal_places=2)


class TrialBalanceSerializer(serializers.Serializer):
    """Serializer for complete trial balance report."""
    
    as_of_date = serializers.DateTimeField()
    currency = serializers.CharField(required=False)
    lines = TrialBalanceLineSerializer(many=True)
    total_debits = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_credits = serializers.DecimalField(max_digits=15, decimal_places=2)
    is_balanced = serializers.BooleanField()


class BalanceSheetLineSerializer(serializers.Serializer):
    """Serializer for balance sheet line item."""
    
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)


class BalanceSheetSectionSerializer(serializers.Serializer):
    """Serializer for balance sheet section (Assets/Liabilities/Equity)."""
    
    section_name = serializers.CharField()
    accounts = BalanceSheetLineSerializer(many=True)
    total = serializers.DecimalField(max_digits=15, decimal_places=2)


class BalanceSheetSerializer(serializers.Serializer):
    """Serializer for complete balance sheet report."""
    
    as_of_date = serializers.DateTimeField()
    currency = serializers.CharField(required=False)
    assets = BalanceSheetSectionSerializer()
    liabilities = BalanceSheetSectionSerializer()
    equity = BalanceSheetSectionSerializer()
    total_assets = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_liabilities_and_equity = serializers.DecimalField(max_digits=15, decimal_places=2)
    is_balanced = serializers.BooleanField()


class LoanAgingBucketSerializer(serializers.Serializer):
    """Serializer for loan aging bucket."""
    
    bucket_name = serializers.CharField()
    days_range = serializers.CharField()
    loan_count = serializers.IntegerField()
    total_outstanding = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_principal = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_interest = serializers.DecimalField(max_digits=15, decimal_places=2)


class LoanAgingDetailSerializer(serializers.Serializer):
    """Serializer for individual loan in aging report."""
    
    loan_id = serializers.UUIDField()
    borrower_name = serializers.CharField()
    principal_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    outstanding_principal = serializers.DecimalField(max_digits=15, decimal_places=2)
    accrued_interest = serializers.DecimalField(max_digits=15, decimal_places=2)
    disbursed_at = serializers.DateTimeField()
    due_date = serializers.DateField()
    days_overdue = serializers.IntegerField()
    status = serializers.CharField()


class LoanAgingReportSerializer(serializers.Serializer):
    """Serializer for complete loan aging report."""
    
    as_of_date = serializers.DateTimeField()
    currency = serializers.CharField(required=False)
    buckets = LoanAgingBucketSerializer(many=True)
    total_loans = serializers.IntegerField()
    total_outstanding = serializers.DecimalField(max_digits=15, decimal_places=2)
    loans_detail = LoanAgingDetailSerializer(many=True, required=False)
