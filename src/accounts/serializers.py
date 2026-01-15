"""Serializers for accounts app."""

from decimal import Decimal
from rest_framework import serializers
from .models import Account, AccountBalance


class AccountSerializer(serializers.ModelSerializer):
    """Serializer for Account model."""

    current_balance = serializers.SerializerMethodField()
    debit_total = serializers.SerializerMethodField()
    credit_total = serializers.SerializerMethodField()
    hierarchy_string = serializers.CharField(source='get_hierarchy_string', read_only=True)
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id', 'code', 'name', 'description', 'account_type', 'currency',
            'parent', 'is_active', 'is_control_account', 'is_system_account',
            'identifiers', 'created_at', 'updated_at', 'version',
            'current_balance', 'debit_total', 'credit_total',
            'hierarchy_string', 'children_count'
        ]
        read_only_fields = ['created_at', 'updated_at', 'version']

    def get_current_balance(self, obj):
        """Get current account balance."""
        return float(obj.current_balance)

    def get_debit_total(self, obj):
        """Get debit total."""
        return float(obj.debit_total)

    def get_credit_total(self, obj):
        """Get credit total."""
        return float(obj.credit_total)

    def get_children_count(self, obj):
        """Get count of child accounts."""
        return obj.children.count()


class AccountListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for account lists."""

    current_balance = serializers.SerializerMethodField()
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)

    class Meta:
        model = Account
        fields = [
            'id', 'code', 'name', 'account_type', 'account_type_display',
            'currency', 'is_active', 'current_balance'
        ]

    def get_current_balance(self, obj):
        """Get current account balance."""
        return float(obj.current_balance)


class AccountHierarchySerializer(serializers.ModelSerializer):
    """Serializer for account hierarchies."""

    children = serializers.SerializerMethodField()
    current_balance = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = ['id', 'code', 'name', 'account_type', 'current_balance', 'children']

    def get_children(self, obj):
        """Recursively serialize child accounts."""
        children = obj.children.all()
        serializer = AccountHierarchySerializer(children, many=True)
        return serializer.data

    def get_current_balance(self, obj):
        """Get current account balance."""
        return float(obj.current_balance)


class AccountBalanceSerializer(serializers.ModelSerializer):
    """Serializer for account balance snapshots."""

    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = AccountBalance
        fields = [
            'id', 'account', 'account_code', 'account_name',
            'balance_date', 'balance', 'debit_total', 'credit_total', 'updated_at'
        ]
        read_only_fields = ['updated_at']

    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = AccountBalance
        fields = [
            'id', 'account', 'account_code', 'account_name',
            'balance_date', 'balance', 'debit_total', 'credit_total', 'updated_at'
        ]
        read_only_fields = ['updated_at']
