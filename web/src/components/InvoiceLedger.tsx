/**
 * InvoiceLedger component — pure presentation layer.
 *
 * This component has zero business logic. It:
 *   1. Calls useInvoices hook to get typed data.
 *   2. Renders loading, error, or success states.
 *   3. Displays data in a table with status-based styling.
 *
 * All formatting uses standard browser APIs.
 * No calculations, no filtering, no data manipulation.
 */

import type { InvoiceLedgerEntry, InvoiceStatus } from "../types/invoice";
import { useInvoices } from "../hooks/useInvoices";

const STATUS_COLORS: Record<InvoiceStatus, string> = {
  paid: "#22c55e",
  overdue: "#ef4444",
  pending: "#f59e0b",
  unknown: "#9ca3af",
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function StatusBadge({ status }: { readonly status: InvoiceStatus }) {
  return (
    <span
      style={{
        color: STATUS_COLORS[status],
        fontWeight: 600,
        textTransform: "capitalize",
      }}
    >
      {status}
    </span>
  );
}

function InvoiceRow({ entry }: { readonly entry: InvoiceLedgerEntry }) {
  return (
    <tr>
      <td>{entry.invoice_id}</td>
      <td>{entry.customer_name ?? "—"}</td>
      <td>{entry.customer_email ?? "—"}</td>
      <td>{entry.customer_country ?? "—"}</td>
      <td>{entry.customer_segment ?? "—"}</td>
      <td>{formatDate(entry.invoice_date)}</td>
      <td>{formatDate(entry.invoice_due_date)}</td>
      <td><StatusBadge status={entry.invoice_status} /></td>
      <td style={{ textAlign: "right" }}>{entry.line_item_count}</td>
      <td style={{ textAlign: "right" }}>{formatCurrency(entry.invoice_amount)}</td>
      <td style={{ textAlign: "right" }}>{formatCurrency(entry.calculated_invoice_total)}</td>
      <td style={{ textAlign: "right" }}>{formatCurrency(entry.amount_discrepancy)}</td>
      <td style={{ textAlign: "right" }}>{entry.payment_terms_days}</td>
    </tr>
  );
}

export default function InvoiceLedger() {
  const state = useInvoices();

  if (state.status === "loading") {
    return <p role="status">Loading invoice ledger…</p>;
  }

  if (state.status === "error") {
    return (
      <div role="alert">
        <h2>Error loading invoices</h2>
        <p>{state.message}</p>
      </div>
    );
  }

  const { data } = state;

  return (
    <section>
      <header style={{ marginBottom: "1rem" }}>
        <h1>Invoice Ledger</h1>
        <p>
          {data.count} invoices · API contract {data.version}
        </p>
      </header>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
              <th>Invoice</th>
              <th>Customer</th>
              <th>Email</th>
              <th>Country</th>
              <th>Segment</th>
              <th>Issued</th>
              <th>Due</th>
              <th>Status</th>
              <th style={{ textAlign: "right" }}>Items</th>
              <th style={{ textAlign: "right" }}>Amount</th>
              <th style={{ textAlign: "right" }}>Calculated</th>
              <th style={{ textAlign: "right" }}>Discrepancy</th>
              <th style={{ textAlign: "right" }}>Terms (days)</th>
            </tr>
          </thead>
          <tbody>
            {data.data.map((entry) => (
              <InvoiceRow key={entry.invoice_id} entry={entry} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
