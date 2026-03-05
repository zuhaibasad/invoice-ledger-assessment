import os
from pathlib import Path
import glob
import duckdb
import yaml


CONFIG_FILE_PATH = Path(__file__).parent.parent / 'config.yml'

def load_config(config_file_path):

    file = open(config_file_path, 'r')
    config = yaml.safe_load(file)
    return config

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
    config = load_config(CONFIG_FILE_PATH)
    db_path = config['database']['path']
    raw_schema = config['schemas']['raw']
    conn = duckdb.connect('invoice_warehouse.duckdb')
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
    load_csv_files_to_duckdb(conn, schema=raw_schema, table_name='invoices', table_schema=TABLE_SCHEMAS['invoices'], csv_file_path='raw_sample_data/invoices.csv')
    load_csv_files_to_duckdb(conn, schema=raw_schema, table_name='customers', table_schema=TABLE_SCHEMAS['customers'], csv_file_path='raw_sample_data/customers.csv')
    load_csv_files_to_duckdb(conn, schema=raw_schema, table_name='invoice_line_items', table_schema=TABLE_SCHEMAS['invoice_line_items'], csv_file_path='raw_sample_data/invoice_line_items.csv')
    
    # Display summary of loaded tables
    tables = conn.execute(f"""SELECT table_name FROM information_schema.tables WHERE table_schema='{raw_schema}'""").fetchall()
    print(f"\nTotal tables created: {len(tables)}")

    conn.close()


if __name__ == '__main__':
    main()
