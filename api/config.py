import os
from pydantic_settings import BaseSettings

DB_PATH = os.environ.get("WAREHOUSE_PATH", "data/invoice_warehouse.duckdb")


class Settings(BaseSettings):
    """Immutable application settings, loaded once at startup."""
    
    app_name: str = "Invoice Ledger API"
    app_version: str = "1.0.0"
    duckdb_path: str = DB_PATH
    debug: bool = False

    model_config = {"env_prefix": "LEDGER_"}


settings = Settings()
