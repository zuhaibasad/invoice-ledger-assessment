"""Tests for the V1 Pydantic contract.

These tests validate that the contract enforces its constraints.
A rigid contract should:
    - Accept valid data matching the dbt mart schema.
    - Reject data that violates type, nullability, or range constraints.
    - Handle nullable fields (customer_email) gracefully.

No database required — these are pure unit tests.
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from contracts.v1 import InvoiceLedgerEntry, InvoiceLedgerResponse, InvoiceStatus


VALID_ENTRY = {
     "invoice_id": 1001,
    "customer_id": 1,
    "line_item_count": 3,
    "payment_terms_days": 30,
    "invoice_amount": 1850.00,
    "calculated_invoice_total": 1850.00,
    "amount_discrepancy": 0.00,
    "invoice_date": date(2024, 1, 15),
    "invoice_due_date": date(2024, 2, 15),
    "invoice_status": "paid",
    "customer_name": "Acme Corp",
    "customer_email": "billing@acme.com",
    "customer_country": "US",
    "customer_segment": "Enterprise"
}

class TestInvoiceLedgerEntry:

    def test_accepts_valid_entry(self) -> None:
        entry = InvoiceLedgerEntry(**VALID_ENTRY)
        assert entry.invoice_id == 1001
        assert entry.invoice_status == InvoiceStatus.PAID

    def test_accepts_nullable_email(self) -> None:
        data = {**VALID_ENTRY, "customer_email": None}
        entry = InvoiceLedgerEntry(**data)
        assert entry.customer_email is None

    def test_accepts_nullable_customer_id(self) -> None:
        data = {**VALID_ENTRY, "customer_id": None}
        entry = InvoiceLedgerEntry(**data)
        assert entry.customer_id is None

    def test_accepts_all_nullable_customer_fields(self) -> None:
        data = {
            **VALID_ENTRY,
            "customer_id": None,
            "customer_name": None,
            "customer_email": None,
            "customer_country": None,
            "customer_segment": None,
        }
        entry = InvoiceLedgerEntry(**data)
        assert entry.customer_name is None

    def test_accepts_all_valid_statuses(self) -> None:
        for status in ["paid", "overdue", "pending", "unknown"]:
            data = {**VALID_ENTRY, "invoice_status": status}
            entry = InvoiceLedgerEntry(**data)
            assert entry.invoice_status.value == status

    def test_rejects_invalid_status(self) -> None:
        data = {**VALID_ENTRY, "invoice_status": "deleted"}
        with pytest.raises(ValidationError):
            InvoiceLedgerEntry(**data)

    def test_rejects_negative_line_item_count(self) -> None:
        data = {**VALID_ENTRY, "line_item_count": -1}
        with pytest.raises(ValidationError):
            InvoiceLedgerEntry(**data)

    def test_rejects_negative_invoice_amount(self) -> None:
        data = {**VALID_ENTRY, "invoice_amount": -100.00}
        with pytest.raises(ValidationError):
            InvoiceLedgerEntry(**data)

    def test_rejects_negative_calculated_total(self) -> None:
        data = {**VALID_ENTRY, "calculated_invoice_total": -50.00}
        with pytest.raises(ValidationError):
            InvoiceLedgerEntry(**data)

    def test_accepts_negative_discrepancy(self) -> None:
        """Discrepancy CAN be negative — it's a difference, not an amount."""
        data = {**VALID_ENTRY, "amount_discrepancy": -25.50}
        entry = InvoiceLedgerEntry(**data)
        assert entry.amount_discrepancy == -25.50

    def test_accepts_zero_total_for_empty_invoices(self) -> None:
        data = {
            **VALID_ENTRY,
            "line_item_count": 0,
            "invoice_amount": 0.00,
            "calculated_invoice_total": 0.00,
            "amount_discrepancy": 0.00,
        }
        entry = InvoiceLedgerEntry(**data)
        assert entry.calculated_invoice_total == 0.00

    def test_rejects_missing_required_field(self) -> None:
        data = {**VALID_ENTRY}
        del data["invoice_id"]
        with pytest.raises(ValidationError):
            InvoiceLedgerEntry(**data)

class TestInvoiceLedgerResponse:

    def test_envelope_structure(self) -> None:
        entry = InvoiceLedgerEntry(**VALID_ENTRY)
        response = InvoiceLedgerResponse(data=[entry], count=1)
        assert response.count == 1
        assert response.version == "v1"
        assert len(response.data) == 1

    def test_empty_response_is_valid(self) -> None:
        response = InvoiceLedgerResponse(data=[], count=0)
        assert response.data == []
        assert response.count == 0