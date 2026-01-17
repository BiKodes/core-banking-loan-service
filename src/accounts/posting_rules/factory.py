"""Posting rules registry and factory."""

import logging

from .base import UnknownEventPostingRule
from .loan_operations import (
    LoanDisbursement,
    LoanInterestAccrual,
    LoanRepayment,
    LoanWriteOff,
)

logger = logging.getLogger(__name__)

POSTING_RULES_REGISTRY = {
    'loan.disbursed': LoanDisbursement,
    'loan.repayment_received': LoanRepayment,
    'loan.written_off': LoanWriteOff,
    'loan.interest_accrued': LoanInterestAccrual,
}


class PostingRuleFactory:
    """Factory for creating and retrieving posting rules."""

    @staticmethod
    def get_posting_rule(event_type):
        """
        Get posting rule for an event type.
        """
        rule_class = POSTING_RULES_REGISTRY.get(
            event_type, UnknownEventPostingRule
        )
        return rule_class()

    @staticmethod
    def process_event(event_type, event_data):
        """
        Process an event with the appropriate posting rule.
        """
        rule = PostingRuleFactory.get_posting_rule(event_type)
        logger.info(
            f"Processing event type: {event_type} with rule: {rule.__class__.__name__}"
        )
        return rule.process(event_data)

    @staticmethod
    def register_rule(event_type, rule_class):
        """
        Register a new posting rule.
        """
        POSTING_RULES_REGISTRY[event_type] = rule_class
        logger.info(
            f"Registered posting rule for {event_type}: {rule_class.__name__}"
        )
