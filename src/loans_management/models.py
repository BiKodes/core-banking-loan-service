"""Loan management domain models."""

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from src.accounts.models import CURRENCY_CHOICES
from src.common.models import TenantAwareModel


class TimeStampedModel(TenantAwareModel):
    """Abstract base with created/updated timestamps and organization scoping."""

    class Meta:
        abstract = True


class Borrower(TimeStampedModel):
    """Minimal borrower record."""

    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    id_number = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.full_name


class Lender(TimeStampedModel):
    """Represents a lender/pool participant."""

    name = models.CharField(max_length=255)
    capital_account_code = models.CharField(
        max_length=20,
        help_text="Account code representing lender capital (liability).",
        default="2110",
    )

    class Meta:
        unique_together = [('organization', 'name')]

    def __str__(self):
        return self.name


class Loan(TimeStampedModel):
    """Loan master record with accounting integration."""

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("DISBURSED", "Disbursed"),
        ("ACTIVE", "Active"),
        ("REPAID", "Repaid"),
        ("DEFAULTED", "Defaulted"),
        ("WRITTEN_OFF", "Written Off"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    borrower = models.ForeignKey(
        Borrower, on_delete=models.PROTECT, related_name="loans"
    )
    lender = models.ForeignKey(
        Lender, on_delete=models.PROTECT, related_name="loans"
    )

    principal_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(
        max_length=3, choices=CURRENCY_CHOICES, default="KES"
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Annual interest rate (percentage).",
    )
    term_months = models.PositiveIntegerField(default=12)
    origination_fee = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="PENDING"
    )
    disbursed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)

    outstanding_principal = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    accrued_interest = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    version = models.PositiveIntegerField(
        default=0, help_text="Optimistic locking version."
    )

    loans_receivable_code = models.CharField(max_length=20, default="1210")
    cash_account_code = models.CharField(max_length=20, default="1110")
    fee_receivable_code = models.CharField(max_length=20, default="1220")
    fee_income_code = models.CharField(max_length=20, default="4210")
    interest_income_code = models.CharField(max_length=20, default="4100")
    interest_receivable_code = models.CharField(max_length=20, default="1220")
    bad_debt_expense_code = models.CharField(max_length=20, default="5100")

    def __str__(self):
        return f"Loan {self.id} - {self.borrower.full_name}"

    def clean(self):
        if self.principal_amount <= 0:
            raise ValidationError("Principal amount must be greater than zero.")
        if self.interest_rate < 0:
            raise ValidationError("Interest rate cannot be negative.")

    def save(self, *args, **kwargs):
        """Implement optimistic locking and validation."""
        self.full_clean()
        if self.pk:
            current = Loan.objects.filter(pk=self.pk).first()
            if current and current.version != self.version:
                raise ValidationError(
                    "Concurrent update detected. Please reload and retry."
                )
            self.version = (self.version or 0) + 1
        super().save(*args, **kwargs)

    @property
    def is_repaid(self):
        return self.status == "REPAID" or self.outstanding_principal <= 0

    def update_outstanding(
        self,
        principal_delta: Decimal,
        interest_delta: Decimal = Decimal("0.00"),
    ):
        """Utility to adjust outstanding balances safely."""
        self.outstanding_principal = (
            self.outstanding_principal or Decimal("0.00")
        ) + principal_delta
        self.accrued_interest = (
            self.accrued_interest or Decimal("0.00")
        ) + interest_delta
        if self.outstanding_principal < 0:
            self.outstanding_principal = Decimal("0.00")


class LoanRepayment(TimeStampedModel):
    """Repayment record tied to a loan."""

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("POSTED", "Posted"),
    )

    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name="repayments"
    )
    idempotency_key = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    principal_component = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    interest_component = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    paid_at = models.DateTimeField(default=timezone.now)
    external_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="PENDING"
    )

    class Meta:
        unique_together = [('organization', 'idempotency_key')]
        indexes = [
            models.Index(fields=["loan", "paid_at"]),
            models.Index(fields=["idempotency_key"]),
        ]

    def __str__(self):
        return f"Repayment {self.id} for Loan {self.loan_id}"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError("Repayment amount must be greater than zero.")
        if self.principal_component + self.interest_component != self.amount:
            raise ValidationError(
                "Principal + interest must equal total amount."
            )


class LoanEvent(TimeStampedModel):
    """Audit log of loan lifecycle events processed."""

    EVENT_TYPES = (
        ("DISBURSEMENT", "Disbursement"),
        ("REPAYMENT", "Repayment"),
        ("WRITE_OFF", "Write Off"),
        ("ACCRUAL", "Interest Accrual"),
    )

    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name="events"
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    idempotency_key = models.CharField(max_length=100, db_index=True)
    journal_entry = models.ForeignKey(
        'journal.JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loan_events",
    )
    payload = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["loan", "event_type"]),
            models.Index(fields=["idempotency_key"]),
        ]

    def __str__(self):
        return f"{self.event_type} for Loan {self.loan_id}"
