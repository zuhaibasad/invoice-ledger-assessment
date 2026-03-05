import duckdb
import os

DB_PATH = os.environ.get("WAREHOUSE_PATH", "data/invoice_warehouse.duckdb")
CSV_DIR_PATH = os.environ.get("RAW_DATA_PATH", "data/raw_sample_data/")


def load_csv_files_to_duckdb(conn, schema, table_name, table_schema, csv_file_path):
    """
    Load CSV files to duckdb.
    Args:
        conn: DuckDB connection object
        table_name: Name of the table to create/replace
        csv_file_path: Path to the CSV file
    """
    
    try:
            conn.execute(f"""
                CREATE OR REPLACE TABLE {schema}.{table_name} (
                    {table_schema}
                );
                COPY {schema}.{table_name} FROM '{csv_file_path}' (HEADER TRUE);
            """)
            print(f"Loaded {table_name} into DuckDB")
    except Exception as e:
            print(f"Error loading {csv_file_path}: {str(e)}")
    

def main():
   
    raw_schema = "raw"
    conn = duckdb.connect(DB_PATH)
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {raw_schema}")
    TABLE_SCHEMAS = {
        "invoices": """
            invoice_id    INTEGER,
            customer_id   INTEGER,
            amount        VARCHAR,
            status        VARCHAR,
            invoice_date  DATE,
            due_date      DATE
        """,
        "customers": """
            customer_id   INTEGER,
            customer_name VARCHAR,
            country       VARCHAR,
            segment       VARCHAR,
            email         VARCHAR
        """,
        "invoice_line_items": """
            line_item_id  INTEGER,
            invoice_id    INTEGER,
            product_name  VARCHAR,
            quantity      INTEGER,
            unit_price    VARCHAR
        """
    }
    load_csv_files_to_duckdb(conn, schema=raw_schema, table_name='invoices', table_schema=TABLE_SCHEMAS['invoices'], csv_file_path=f'{CSV_DIR_PATH}/invoices.csv')
    load_csv_files_to_duckdb(conn, schema=raw_schema, table_name='customers', table_schema=TABLE_SCHEMAS['customers'], csv_file_path=f'{CSV_DIR_PATH}/customers.csv')
    load_csv_files_to_duckdb(conn, schema=raw_schema, table_name='invoice_line_items', table_schema=TABLE_SCHEMAS['invoice_line_items'], csv_file_path=f'{CSV_DIR_PATH}/invoice_line_items.csv')

    # Display summary of loaded tables
    tables = conn.execute(f"""SELECT table_name FROM information_schema.tables WHERE table_schema='{raw_schema}'""").fetchall()
    print(f"\nTotal tables created: {len(tables)}")

    conn.close()


if __name__ == '__main__':
    main()
