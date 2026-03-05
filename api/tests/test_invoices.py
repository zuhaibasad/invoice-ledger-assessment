"""Integration tests for the V1 invoices endpoint.

These tests validate the full request/response cycle using
FastAPI's test client. They require a populated DuckDB database
with a successful dbt deployment (public.mart_invoice_ledger must exist).

Run after: make deploy (or dbt build --target blue/green)
"""

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


class TestHealthEndpoint:
    """Validates the liveness probe."""

    def test_returns_200(self) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_response_shape(self) -> None:
        data = client.get("/api/health").json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "active_schema" in data


class TestInvoicesEndpoint:
    """Validates the V1 invoice ledger endpoint."""

    def test_returns_200(self) -> None:
        response = client.get("/api/v1/invoices")
        assert response.status_code == 200

    def test_response_has_envelope_fields(self) -> None:
        data = client.get("/api/v1/invoices").json()
        assert "data" in data
        assert "count" in data
        assert "version" in data
        assert data["version"] == "v1"

    def test_count_matches_data_length(self) -> None:
        data = client.get("/api/v1/invoices").json()
        assert data["count"] == len(data["data"])

    def test_entries_have_all_contracted_fields(self) -> None:
        contracted_fields = {
                "invoice_id",
                "customer_id",
                "line_item_count",
                "payment_terms_days",
                "invoice_amount",
                "calculated_invoice_total",
                "amount_discrepancy",
                "invoice_date",
                "invoice_due_date",
                "invoice_status",
                "customer_name",
                "customer_email",
                "customer_country",
                "customer_segment"
        }
        data = client.get("/api/v1/invoices").json()
        if data["count"] > 0:
            assert set(data["data"][0].keys()) == contracted_fields

    def test_no_extra_fields_leaked(self) -> None:
        """The explicit SELECT in the query should prevent column leaks."""
        contracted_fields = {
                "invoice_id",
                "customer_id",
                "line_item_count",
                "payment_terms_days",
                "invoice_amount",
                "calculated_invoice_total",
                "amount_discrepancy",
                "invoice_date",
                "invoice_due_date",
                "invoice_status",
                "customer_name",
                "customer_email",
                "customer_country",
                "customer_segment"
        }
        data = client.get("/api/v1/invoices").json()
        for entry in data["data"]:
            assert set(entry.keys()) == contracted_fields

    def test_statuses_are_lowercase(self) -> None:
        data = client.get("/api/v1/invoices").json()
        for entry in data["data"]:
            assert entry["invoice_status"] == entry["invoice_status"].lower()

    def test_totals_are_non_negative(self) -> None:
        data = client.get("/api/v1/invoices").json()
        for entry in data["data"]:
            assert float(entry["invoice_amount"]) >= 0

    def test_line_item_counts_are_non_negative(self) -> None:
        data = client.get("/api/v1/invoices").json()
        for entry in data["data"]:
            assert entry["line_item_count"] >= 0

    def test_endpoint_is_idempotent(self) -> None:
        """Identical calls must produce identical results."""
        first = client.get("/api/v1/invoices").json()
        second = client.get("/api/v1/invoices").json()
        assert first == second