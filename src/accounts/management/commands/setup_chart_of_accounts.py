"""Management command to create default chart of accounts."""

from django.core.management.base import BaseCommand
from django.db import transaction
from src.accounts.models import Account


class Command(BaseCommand):
    """Create default chart of accounts for core banking system."""

    help = 'Creates a default chart of accounts for the loan management system'

    @transaction.atomic
    def handle(self, *args, **options):
        """Execute command."""
        self.stdout.write(self.style.SUCCESS('Creating default chart of accounts...'))

        coa = [
            # ASSETS
            {
                'code': '1000',
                'name': 'Current Assets',
                'account_type': 'ASSET',
                'is_control_account': True,
                'currency': 'KES',
            },
            {
                'code': '1100',
                'name': 'Cash & Cash Equivalents',
                'account_type': 'ASSET',
                'parent_code': '1000',
                'is_control_account': True,
                'currency': 'KES',
            },
            {
                'code': '1110',
                'name': 'M-Pesa Cash Account',
                'account_type': 'ASSET',
                'parent_code': '1100',
                'identifiers': 'mobile_money,cash',
                'currency': 'KES',
            },
            {
                'code': '1120',
                'name': 'Bank Account',
                'account_type': 'ASSET',
                'parent_code': '1100',
                'identifiers': 'bank',
                'currency': 'KES',
            },
            {
                'code': '1200',
                'name': 'Loans Receivable',
                'account_type': 'ASSET',
                'parent_code': '1000',
                'is_control_account': True,
                'identifiers': 'loans',
                'currency': 'KES',
            },
            {
                'code': '1210',
                'name': 'Loan Principal Receivable',
                'account_type': 'ASSET',
                'parent_code': '1200',
                'currency': 'KES',
            },
            {
                'code': '1220',
                'name': 'Loan Origination Fee Receivable',
                'account_type': 'ASSET',
                'parent_code': '1200',
                'currency': 'KES',
            },

            # LIABILITIES
            {
                'code': '2000',
                'name': 'Current Liabilities',
                'account_type': 'LIABILITY',
                'is_control_account': True,
                'currency': 'KES',
            },
            {
                'code': '2100',
                'name': 'Lender Capital',
                'account_type': 'LIABILITY',
                'parent_code': '2000',
                'is_control_account': True,
                'identifiers': 'capital',
                'currency': 'KES',
            },
            {
                'code': '2110',
                'name': 'Lender Capital Account - Pool A',
                'account_type': 'LIABILITY',
                'parent_code': '2100',
                'currency': 'KES',
            },

            # EQUITY
            {
                'code': '3000',
                'name': 'Equity',
                'account_type': 'EQUITY',
                'is_control_account': True,
                'currency': 'KES',
            },
            {
                'code': '3100',
                'name': 'Retained Earnings',
                'account_type': 'EQUITY',
                'parent_code': '3000',
                'currency': 'KES',
            },

            # INCOME
            {
                'code': '4000',
                'name': 'Operating Income',
                'account_type': 'INCOME',
                'is_control_account': True,
                'currency': 'KES',
            },
            {
                'code': '4100',
                'name': 'Interest Income',
                'account_type': 'INCOME',
                'parent_code': '4000',
                'identifiers': 'interest,income',
                'currency': 'KES',
            },
            {
                'code': '4200',
                'name': 'Fee Income',
                'account_type': 'INCOME',
                'parent_code': '4000',
                'identifiers': 'fee,income',
                'currency': 'KES',
            },
            {
                'code': '4210',
                'name': 'Loan Origination Fee Income',
                'account_type': 'INCOME',
                'parent_code': '4200',
                'currency': 'KES',
            },

            # EXPENSES
            {
                'code': '5000',
                'name': 'Operating Expenses',
                'account_type': 'EXPENSE',
                'is_control_account': True,
                'currency': 'KES',
            },
            {
                'code': '5100',
                'name': 'Bad Debt Expense',
                'account_type': 'EXPENSE',
                'parent_code': '5000',
                'identifiers': 'bad_debt,expense',
                'currency': 'KES',
            },
            {
                'code': '5200',
                'name': 'Operating Expense',
                'account_type': 'EXPENSE',
                'parent_code': '5000',
                'currency': 'KES',
            },
        ]

        created_count = 0
        skipped_count = 0

        for account_data in coa:
            parent = None
            if 'parent_code' in account_data:
                parent_code = account_data.pop('parent_code')
                parent = Account.objects.filter(code=parent_code).first()

            account_data.pop('parent_code', None)

            if parent:
                account_data['parent'] = parent

            account, created = Account.objects.get_or_create(
                code=account_data['code'],
                defaults=account_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created: {account.code} - {account.name}')
                )
            else:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  ⊘ Already exists: {account.code}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n\nChart of Accounts setup complete!\n'
                f'Created: {created_count} accounts\n'
                f'Skipped: {skipped_count} accounts'
            )
        )
