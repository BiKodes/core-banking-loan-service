"""Base infrastructure for accounting posting rules."""

import logging
from abc import ABCMeta, abstractmethod
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from src.accounts.models import Account
from src.journal.models import JournalEntry, JournalEntryLine

logger = logging.getLogger(__name__)


class PostingRuleInterface(metaclass=ABCMeta):
    """Define the contract for all posting rules."""

    def __init__(self):
        """Initialize posting rule."""
        self.setup()

    @abstractmethod
    def setup(self):
        """Set up posting rule."""

    @transaction.atomic
    @abstractmethod
    def process(self, event):
        """Entry point for posting rule processing."""


class PostingRuleBase(PostingRuleInterface):
    """Base class for accounting posting rules."""

    def setup(self):
        """Set up posting rule."""
        self.errors = []

    def blow_up_if_errors(self, errors=None):
        """Raise validation errors if any exist."""
        errors = errors or self.errors
        if errors:
            raise ValidationError({"__all__": errors})

    def get_account(self, account_code):
        """Fetch an account by code."""
        try:
            return Account.objects.get(code=account_code)
        except Account.DoesNotExist:
            msg = f"Account with code {account_code} does not exist."
            logger.error(msg)
            self.errors.append(msg)
            return None

    def create_journal_entry(self, idempotency_key, description, entries_data):
        """
        Create a journal entry with multiple line items.
        """
        debit_total = Decimal('0')
        credit_total = Decimal('0')

        for entry in entries_data:
            amount = Decimal(str(entry['amount']))
            if entry['entry_type'] == 'DR':
                debit_total += amount
            else:
                credit_total += amount

        if debit_total != credit_total:
            msg = f"Entries do not balance. Debits: {debit_total}, Credits: {credit_total}"
            logger.error(msg)
            self.errors.append(msg)
            self.blow_up_if_errors()

        journal_entry = JournalEntry.objects.create(
            idempotency_key=idempotency_key,
            description=description,
            status="POSTED"
        )

        for entry in entries_data:
            account = self.get_account(entry['account_code'])
            if not account:
                self.blow_up_if_errors()

            if account.is_control_account:
                msg = f"Cannot post to control account {account.code}"
                logger.error(msg)
                self.errors.append(msg)
                self.blow_up_if_errors()

            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=account,
                entry_type=entry['entry_type'],
                amount=Decimal(str(entry['amount'])),
                description=entry.get('description', '')
            )

        return journal_entry


class UnknownEventPostingRule(PostingRuleBase):
    """Fallback for unknown events."""

    def process(self, event):
        """Log unknown event and do nothing."""
        logger.error(
            f"Unknown event received with no posting rules configured: {event}"
        )
