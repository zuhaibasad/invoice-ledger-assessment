import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import InvoiceLedger from "../components/InvoiceLedger";
import type { InvoiceLedgerResponse } from "../types/invoice";

const MOCK_RESPONSE: InvoiceLedgerResponse = {
  data: [
    {
      invoice_id: 1001,
      customer_id: 1,
      line_item_count: 3,
      payment_terms_days: 30,
      invoice_amount: 1850.0,
      calculated_invoice_total: 1850.0,
      amount_discrepancy: 0.0,
      invoice_date: "2024-01-15",
      invoice_due_date: "2024-02-15",
      invoice_status: "paid",
      customer_name: "Acme Corp",
      customer_email: "billing@acme.com",
      customer_country: "US",
      customer_segment: "Enterprise",
    },
    {
      invoice_id: 1005,
      customer_id: null,
      line_item_count: 0,
      payment_terms_days: 15,
      invoice_amount: 0.0,
      calculated_invoice_total: 0.0,
      amount_discrepancy: 0.0,
      invoice_date: "2024-02-15",
      invoice_due_date: "2024-03-15",
      invoice_status: "pending",
      customer_name: null,
      customer_email: null,
      customer_country: null,
      customer_segment: null,
    },
  ],
  count: 2,
  version: "v1",
};

function mockFetchSuccess(): void {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(MOCK_RESPONSE),
  });
}

function mockFetchFailure(status: number): void {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status,
    statusText: "Internal Server Error",
  });
}

function mockFetchNetworkError(): void {
  global.fetch = vi.fn().mockRejectedValue(new Error("Network error"));
}

describe("InvoiceLedger", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows loading state initially", () => {
    global.fetch = vi.fn().mockReturnValue(new Promise(() => {}));
    render(<InvoiceLedger />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });

  it("renders invoice data on success", async () => {
    mockFetchSuccess();
    render(<InvoiceLedger />);

    await waitFor(() => {
      expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    });
    expect(screen.getByText("2 invoices · API contract v1")).toBeInTheDocument();
  });

  it("renders null fields as dash", async () => {
    mockFetchSuccess();
    render(<InvoiceLedger />);

    await waitFor(() => {
      const dashes = screen.getAllByText("—");
      expect(dashes.length).toBeGreaterThan(0);
    });
  });

  it("shows error state on API failure", async () => {
    mockFetchFailure(500);
    render(<InvoiceLedger />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  it("shows error state on network failure", async () => {
    mockFetchNetworkError();
    render(<InvoiceLedger />);

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("formats currency correctly", async () => {
    mockFetchSuccess();
    render(<InvoiceLedger />);

    await waitFor(() => {
      expect(screen.getByText("$1,850.00")).toBeInTheDocument();
      expect(screen.getByText("$0.00")).toBeInTheDocument();
    });
  });

  it("displays status badges with correct text", async () => {
    mockFetchSuccess();
    render(<InvoiceLedger />);

    await waitFor(() => {
      expect(screen.getByText("paid")).toBeInTheDocument();
      expect(screen.getByText("pending")).toBeInTheDocument();
    });
  });
});
