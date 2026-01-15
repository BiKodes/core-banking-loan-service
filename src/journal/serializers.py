"""Serializers for journal app."""

from rest_framework import serializers
from django.db import transaction
from decimal import Decimal

from .models import (
    JournalEntry, JournalEntryLine, TransactionIdempotencyCache,
    TRANSACTION_STATUS
)
from accounts.models import Account


class JournalEntryLineSerializer(serializers.ModelSerializer):
    """Serializer for JournalEntryLine."""

    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = JournalEntryLine
        fields = [
            'id', 'account', 'account_code', 'account_name',
            'entry_type', 'amount', 'description', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class JournalEntrySerializer(serializers.ModelSerializer):
    """Serializer for JournalEntry (read-only)."""

    lines = JournalEntryLineSerializer(many=True, read_only=True)
    total_debit = serializers.SerializerMethodField()
    total_credit = serializers.SerializerMethodField()
    is_balanced = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'idempotency_key', 'description', 'status',
            'lines', 'total_debit', 'total_credit', 'is_balanced',
            'reversed_by', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_total_debit(self, obj):
        """Calculate total debit amount."""
        return float(obj.lines.filter(entry_type='DR').aggregate(
            total=serializers.Sum('amount')
        )['total'] or 0)

    def get_total_credit(self, obj):
        """Calculate total credit amount."""
        return float(obj.lines.filter(entry_type='CR').aggregate(
            total=serializers.Sum('amount')
        )['total'] or 0)

    def get_is_balanced(self, obj):
        """Check if journal entry is balanced."""
        return obj.is_balanced()


class JournalEntryLineCreateUpdateSerializer(serializers.Serializer):
    """Serializer for creating/updating journal entry lines."""

    account_code = serializers.CharField(max_length=20)
    entry_type = serializers.ChoiceField(choices=['DR', 'CR'])
    amount = serializers.DecimalField(max_digits=19, decimal_places=2)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_amount(self, value):
        """Validate amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_entry_type(self, value):
        """Validate entry type is valid."""
        if value not in ['DR', 'CR']:
            raise serializers.ValidationError("Entry type must be 'DR' or 'CR'.")
        return value


class JournalEntryCreateSerializer(serializers.Serializer):
    """Serializer for creating journal entries."""

    idempotency_key = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=1000)
    lines = JournalEntryLineCreateUpdateSerializer(many=True)

    def validate_idempotency_key(self, value):
        """Validate idempotency key is unique."""
        if TransactionIdempotencyCache.objects.filter(idempotency_key=value).exists():
            raise serializers.ValidationError(
                f"Transaction with idempotency key '{value}' already exists."
            )
        return value

    def validate_lines(self, value):
        """Validate lines list."""
        if not value:
            raise serializers.ValidationError("At least one line entry is required.")
        if len(value) < 2:
            raise serializers.ValidationError("At least two line entries are required (debit and credit).")
        return value

    def validate(self, data):
        """Validate the entire journal entry."""
        lines = data.get('lines', [])

        total_debit = Decimal('0')
        total_credit = Decimal('0')

        for line in lines:
            amount = Decimal(str(line['amount']))
            if line['entry_type'] == 'DR':
                total_debit += amount
            else:
                total_credit += amount

        if total_debit != total_credit:
            raise serializers.ValidationError(
                f"Debits ({total_debit}) must equal credits ({total_credit})."
            )

        account_codes = [line['account_code'] for line in lines]
        existing_accounts = Account.objects.filter(
            code__in=account_codes, is_active=True
        ).count()

        if existing_accounts != len(account_codes):
            raise serializers.ValidationError("One or more account codes do not exist.")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """Create journal entry with lines."""
        idempotency_key = validated_data['idempotency_key']
        description = validated_data['description']
        lines_data = validated_data['lines']

        idempotency_cache = TransactionIdempotencyCache.objects.create(
            idempotency_key=idempotency_key
        )

        journal_entry = JournalEntry.objects.create(
            idempotency_key=idempotency_key,
            description=description,
            status='POSTED'
        )

        for line_data in lines_data:
            account = Account.objects.get(code=line_data['account_code'])
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=account,
                entry_type=line_data['entry_type'],
                amount=line_data['amount'],
                description=line_data.get('description', '')
            )

        return journal_entry


class JournalEntryReverseSerializer(serializers.Serializer):
    """Serializer for reversing journal entries."""

    idempotency_key = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=1000, required=False)

    def validate_idempotency_key(self, value):
        """Validate idempotency key is unique."""
        if TransactionIdempotencyCache.objects.filter(idempotency_key=value).exists():
            raise serializers.ValidationError(
                f"Transaction with idempotency key '{value}' already exists."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        """Reverse the journal entry."""
        idempotency_key = validated_data['idempotency_key']
        description = validated_data.get('description')

        journal_entry = self.context.get('journal_entry')

        if not journal_entry:
            raise serializers.ValidationError("Journal entry not provided.")

        if journal_entry.status == 'REVERSED':
            raise serializers.ValidationError("Journal entry is already reversed.")

        if journal_entry.status != 'POSTED':
            raise serializers.ValidationError("Only posted journal entries can be reversed.")

        TransactionIdempotencyCache.objects.create(
            idempotency_key=idempotency_key
        )

        reversed_entry = journal_entry.reverse(
            idempotency_key=idempotency_key,
            description=description or f"Reversal of {journal_entry.description}"
        )

        return reversed_entry


class TransactionIdempotencyCacheSerializer(serializers.ModelSerializer):
    """Serializer for TransactionIdempotencyCache."""

    class Meta:
        model = TransactionIdempotencyCache
        fields = ['id', 'idempotency_key', 'created_at']
        read_only_fields = fields
