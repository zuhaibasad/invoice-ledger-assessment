#!/bin/bash
# deploy.sh — Blue-green deploy logic for Docker.
#
# Replicates the Makefile deploy target:
#   1. Queries deployment_state for active color.
#   2. Picks the inactive color.
#   3. Runs dbt build against the inactive target.
#   4. on-run-end hook swaps proxy view if all tests pass.

set -euo pipefail

DB_PATH="${WAREHOUSE_PATH:-/data/invoice_warehouse.duckdb}"

echo "=== Installing dbt packages ==="
dbt deps --profiles-dir . --project-dir .

# Detect which target to deploy to
TARGET=$(python -c "
import duckdb
try:
    conn = duckdb.connect('${DB_PATH}', read_only=True)
    row = conn.execute('select active_schema from public.deployment_state order by deployed_at desc limit 1').fetchone()
    conn.close()
    print('green' if row and row[0] == 'prod_blue' else 'blue')
except:
    print('blue')
")

echo ">>> Active detection complete. Deploying to ${TARGET} (inactive slot)"

dbt build --target "${TARGET}" --profiles-dir . --project-dir .