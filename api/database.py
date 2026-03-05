"""Read-only DuckDB connection management.

Design decisions:
  - Connections are opened READ-ONLY. The API layer never mutates
    the data warehouse. All writes are dbt's responsibility.
  - The connection is yielded as a FastAPI dependency, ensuring
    cleanup via the generator pattern (no leaked connections).
  - The API queries public.mart_invoice_ledger (the proxy view),
    never a specific deployment schema. This keeps the API
    completely decoupled from the blue-green deployment strategy.
"""

from collections.abc import Generator
from config import settings
import duckdb


def get_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Yield a read-only DuckDB connection.

    Used as a FastAPI dependency. The connection is closed after
    the request completes, preventing resource leaks.
    """
    conn = duckdb.connect(database=settings.duckdb_path, read_only=True)
    try:
        yield conn
    finally:
        conn.close()
