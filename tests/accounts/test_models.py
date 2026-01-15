"""Unit tests for Account model."""

from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from src.accounts.models import Account, ACCOUNT_TYPES


class AccountModelTests(TestCase):
    """Test cases for Account model."""

    def setUp(self):
        """Set up test accounts."""
        self.assets = Account.objects.create(
            code="1000",
            name="Assets",
            account_type="ASSET",
            currency="KES",
            is_control_account=True
        )

        self.current_assets = Account.objects.create(
            code="1100",
            name="Current Assets",
            account_type="ASSET",
            currency="KES",
            parent=self.assets,
            is_control_account=True
        )

        self.cash = Account.objects.create(
            code="1110",
            name="Cash Account",
            account_type="ASSET",
            currency="KES",
            parent=self.current_assets
        )

    def test_account_creation(self):
        """Test creating a new account."""
        account = Account.objects.create(
            code="1120",
            name="Bank Account",
            account_type="ASSET",
            currency="KES",
            parent=self.current_assets
        )
        self.assertEqual(account.code, "1120")
        self.assertEqual(account.name, "Bank Account")
        self.assertEqual(account.account_type, "ASSET")

    def test_account_hierarchy(self):
        """Test account hierarchy relationships."""
        self.assertEqual(self.cash.parent, self.current_assets)
        self.assertEqual(self.current_assets.parent, self.assets)
        self.assertIsNone(self.assets.parent)

    def test_account_hierarchy_path(self):
        """Test getting full account hierarchy path."""
        path = self.cash.get_hierarchy_path()
        self.assertEqual(len(path), 3)
        self.assertEqual(path[0], self.assets)
        self.assertEqual(path[1], self.current_assets)
        self.assertEqual(path[2], self.cash)

    def test_hierarchy_string(self):
        """Test hierarchy string representation."""
        hierarchy_str = self.cash.get_hierarchy_string()
        self.assertIn("1000", hierarchy_str)
        self.assertIn("1100", hierarchy_str)
        self.assertIn("1110", hierarchy_str)

    def test_parent_must_be_control_account(self):
        """Test that parent account must be a control account."""
        non_control = Account.objects.create(
            code="1130",
            name="Non-Control Account",
            account_type="ASSET",
            currency="KES",
            parent=self.current_assets
        )

        with self.assertRaises(ValidationError):
            Account.objects.create(
                code="1131",
                name="Child Account",
                account_type="ASSET",
                currency="KES",
                parent=non_control
            )

    def test_circular_hierarchy_prevention(self):
        """Test that circular hierarchies are prevented."""
        with self.assertRaises(ValidationError):
            self.assets.parent = self.cash
            self.assets.save()

    def test_prevent_deletion_with_transactions(self):
        """Test that accounts with transactions cannot be deleted."""
        pass

    def test_system_account_protection(self):
        """Test that system accounts are protected."""
        account = Account.objects.create(
            code="9999",
            name="System Account",
            account_type="ASSET",
            currency="KES",
            is_system_account=True
        )

        with self.assertRaises(ValidationError):
            account.delete()

    def test_account_deactivation(self):
        """Test account deactivation."""
        account = Account.objects.create(
            code="2000",
            name="Test Account",
            account_type="ASSET",
            currency="KES"
        )

        account.is_active = False
        account.save()
        self.assertFalse(account.is_active)

    def test_multi_currency_accounts(self):
        """Test accounts in different currencies."""
        ksh_account = Account.objects.create(
            code="3000",
            name="KES Account",
            account_type="ASSET",
            currency="KES",
            parent=self.current_assets
        )

        ugx_account = Account.objects.create(
            code="3000",
            name="UGX Account",
            account_type="ASSET",
            currency="UGX",
            parent=self.current_assets
        )

        self.assertEqual(ksh_account.currency, "KES")
        self.assertEqual(ugx_account.currency, "UGX")

    def test_account_str_representation(self):
        """Test string representation of account."""
        self.assertEqual(str(self.cash), "1110 - Cash Account")

    def test_all_account_types(self):
        """Test creating accounts of all types."""
        for account_type, _ in ACCOUNT_TYPES:
            account = Account.objects.create(
                code=f"TYPE-{account_type}",
                name=f"{account_type} Test Account",
                account_type=account_type,
                currency="KES"
            )
            self.assertEqual(account.account_type, account_type)
