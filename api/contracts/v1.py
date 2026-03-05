"""V1 API response contracts for the Invoice Ledger.

These Pydantic models form a rigid contract between the dbt mart
and the API consumer. Every field maps 1:1 to a column in
mart_invoice_ledger_v1.

Contract chain:
    dbt (enforced contract)  → guarantees column names + types
    Pydantic (this file)     → validates every row at serialization
    TypeScript (frontend)    → compile-time type safety

Contract evolution:
    Fields are NEVER removed or renamed in v1.
    Breaking changes require a new version (v2.py) with a
    corresponding dbt mart version and API router version.
"""

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

class InvoiceStatus(str, Enum):
    PAID = "paid"
    OVERDUE = "overdue"
    PENDING = "pending"
    UNKNOWN = "unknown"


class InvoiceLedgerEntry(BaseModel):
   
    """Single row from the invoice ledger mart.

    Field types are chosen to match the dbt contract exactly:
        invoice_id: INTEGER → int
        invoice_amount: DOUBLE → Float
        calculated_invoice_total: DOUBLE -> Float
        amount_discrepancy: DOUBLE -> Float

        invoice_date: DATE → date
        invoice_due_date: DATE → date
        invoice_status: VARCHAR → InvoiceStatus enum

        customer_id: INTEGER → int | None (intentionally nullable)
        customer_name: VARCHAR → str | None (intentionally nullable)
        customer_email: VARCHAR → str | None (intentionally nullable)
        customer_country: VARCHAR → str | None (intentionally nullable)
        customer_segment: VARCHAR → str | None (intentionally nullable)
        line_item_count: INTEGER     → int (ge=0)
        payment_terms_days: INTEGER → int
    """

    invoice_id: int = Field(description="Unique invoice identifier")
    customer_id: int | None = Field(description="Unique customer identifier")
    line_item_count: int = Field(ge=0, description="Number of line items")
    payment_terms_days: int = Field(description="Number of payment terms days")

    invoice_amount: float = Field(ge=0, description="Total amount from the invoices table (may include discrepancies)")
    calculated_invoice_total: float = Field(ge=0, description="Sum of all line item totals")
    amount_discrepancy: float = Field(description="Difference between invoice_amount and calculated_invoice_total")


    invoice_date: date = Field(description="Date the invoice was issued")
    invoice_due_date: date = Field(description="Payment due date")
    
    invoice_status: InvoiceStatus = Field(description="Invoice lifecycle status")
    
    customer_name: str | None = Field(description="just customer name, can be null")
    customer_email: str | None = Field(description="just customer email, can be null")
    customer_country: str | None = Field(description="just customer country, can be null")
    customer_segment: str | None = Field(description="just customer segment, can be null")


    model_config = {"from_attributes": True}


class InvoiceLedgerResponse(BaseModel):
    """Response for the invoice ledger endpoint.

    It provides a stable response structure:
        data -> list of invoice rows
        count -> convenience field (len(data)), avoids client-side counting
        version -> declares which contract version this response uses
    """

    data: list[InvoiceLedgerEntry]
    count: int = Field(ge=0, description="Number of entries returned")
    version: str = Field(default="v1", description="API contract version")