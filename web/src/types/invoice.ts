/**
 * V1 Invoice Ledger TypeScript contracts.
 *
 * These types mirror the Pydantic models in api/contracts/v1/v1.py EXACTLY.
 * Field names, types, and nullability must stay in sync with the backend.
 * Any drift between these types and the Pydantic models is a bug.
 *
 * Contract chain: dbt (enforced) → Pydantic (validated) → TypeScript (typed)
 */

export type InvoiceStatus = "paid" | "overdue" | "pending" | "unknown";

export interface InvoiceLedgerEntry {
  readonly invoice_id: number;
  readonly customer_id: number | null;
  readonly line_item_count: number;
  readonly payment_terms_days: number;

  readonly invoice_amount: number;
  readonly calculated_invoice_total: number;
  readonly amount_discrepancy: number;

  readonly invoice_date: string;
  readonly invoice_due_date: string;

  readonly invoice_status: InvoiceStatus;

  readonly customer_name: string | null;
  readonly customer_email: string | null;
  readonly customer_country: string | null;
  readonly customer_segment: string | null;
}

export interface InvoiceLedgerResponse {
  readonly data: readonly InvoiceLedgerEntry[];
  readonly count: number;
  readonly version: string;
}
