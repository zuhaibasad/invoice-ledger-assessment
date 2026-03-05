"""V1 Invoice Ledger endpoint.

This router is a thin serving layer. It reads from the public proxy view.
Validates each row through the Pydantic contract.
returns the validated response.

No business logic. No data transformation. No side effects.
The endpoint is idempotent: identical calls produce identical results.

The query reads from public.mart_invoice_ledger. the proxy view
managed by dbt deployment. The API has zero concern with which 
color (prod_blue/prod_green) is currently active.
"""

from fastapi import APIRouter, Depends
from duckdb import DuckDBPyConnection

from contracts.v1 import InvoiceLedgerEntry, InvoiceLedgerResponse
from database import get_connection


router = APIRouter(prefix="/invoices", tags=["invoices"])

# Explicit column list acts as a secondary guard: if dbt adds a column
# to the mart, the API only returns contracted fields. No leaky columns.
LEDGER_QUERY = """
    select
        invoice_id,
        customer_id,
        customer_name,
        customer_country,
        customer_segment,
        customer_email,
        invoice_amount,
        invoice_status,
        invoice_date,
        invoice_due_date,
        payment_terms_days,
        line_item_count,
        calculated_invoice_total,
        amount_discrepancy,
    from public.mart_invoice_ledger
"""


@router.get(
    "",
    response_model=InvoiceLedgerResponse,
    summary="List all processed invoices",
    description=(
        "Returns the complete invoice ledger from the latest dbt deployment. "
        "Data is served from a proxy view that transparently points to the "
        "active blue-green deployment schema."
    ),
)
def list_invoices(
    conn: DuckDBPyConnection = Depends(get_connection),
    ) -> InvoiceLedgerResponse:
    
    """Fetch and validate all invoice ledger entries."""
    rows = conn.execute(LEDGER_QUERY).fetchall()
    columns = [desc[0] for desc in conn.description]
    entries = [
        InvoiceLedgerEntry(**dict(zip(columns, row)))
        for row in rows
    ]

    return InvoiceLedgerResponse(data=entries, count=len(entries))