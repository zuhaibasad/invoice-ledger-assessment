/**
 * useInvoices hook — encapsulates data fetching for the invoice ledger.
 *
 * Design decisions:
 *   - Returns a discriminated union of loading/error/success states.
 *     The consumer component never has to guess which state it's in.
 *   - No data transformation. Fetches and returns typed data as-is.
 *   - AbortController prevents state updates on unmounted components.
 *   - Zero side effects beyond the fetch itself.
 */

import { useEffect, useState } from "react";
import type { InvoiceLedgerResponse } from "../types/invoice";

const API_URL = "/api/v1/invoices";

interface LoadingState {
  status: "loading";
}

interface ErrorState {
  status: "error";
  message: string;
}

interface SuccessState {
  status: "success";
  data: InvoiceLedgerResponse;
}

export type InvoiceState = LoadingState | ErrorState | SuccessState;

export function useInvoices(): InvoiceState {
  const [state, setState] = useState<InvoiceState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    async function fetchInvoices(): Promise<void> {
      try {
        const response = await fetch(API_URL, { signal: controller.signal });

        if (!response.ok) {
          setState({
            status: "error",
            message: `API returned ${response.status}: ${response.statusText}`,
          });
          return;
        }

        const data: InvoiceLedgerResponse = await response.json();
        setState({ status: "success", data });
      } catch (error: unknown) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        const message =
          error instanceof Error ? error.message : "Unknown error occurred";
        setState({ status: "error", message });
      }
    }

    fetchInvoices();

    return () => controller.abort();
  }, []);

  return state;
}
