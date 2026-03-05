# Invoice Ledger: dbt orchestration with Blue Green Deployment
#
# Usage:
#   make dev        to build into dev schema
#   make deploy     production deploy which serves API with 
#					blue-green strategy (detects active/inactive schema, builds, swaps)
#   make status     Show active deployment color/schema and deployed_at date time
#   make test       Run dbt tests only (no model build)
#   make clean      Drop blue + green schemas for fresh start
#
# The deploy target auto detects which color is active by querying
# public.deployment_state and deploys to the INACTIVE one.
# Once all tests all passed on the inactive schema then 
# the on-run-end hook/macro in dbt swaps the proxy view (in public schema) that server FastAPI

.PHONY: help dev deploy status test clean

.DEFAULT_GOAL := help

help:
	@echo "Usage:"
	@echo "  make dev        Build into dev schema (safe sandbox)"
	@echo "  make deploy     Auto blue-green deploy (detects color, builds, swaps)"
	@echo "  make status     Show active deployment color and timestamp"
	@echo "  make test       Run dbt tests only (no model build)"
	@echo "  make clean      Drop blue + green schemas for fresh start (dangerous, only for this assessment purpose)"


DBT_DIR  := dbt
DBT_ARGS := --profiles-dir $(DBT_DIR) --project-dir $(DBT_DIR)
DB_PATH  := data/invoice_warehouse.duckdb

# Development build
dev:
	dbt build $(DBT_ARGS)

# Blue-green production deploy -----------------------
# 1. Queries deployment_state for the active color
# 2. Picks the inactive color as the dbt target
# 3. Runs dbt build (models + tests)
# 4. on-run-end hook swaps proxy view only if all passed
deploy:
	@TARGET=$$(python -c "import duckdb; \
	conn = duckdb.connect('$(DB_PATH)', read_only=True); \
	row = conn.execute('select active_schema from public.deployment_state order by deployed_at desc limit 1').fetchone(); \
	print('green' if row and row[0] == 'prod_blue' else 'blue'); \
	conn.close() if conn else None") && \
	echo ">>> Deploying to $$TARGET (inactive slot)" && \
	dbt build --target $$TARGET $(DBT_ARGS)

# Deployment status -------------------------------------
status:
	@python -c "import duckdb; \
	conn = duckdb.connect('$(DB_PATH)', read_only=True); \
	row = conn.execute('select active_schema, deployed_at from public.deployment_state order by deployed_at desc limit 1').fetchone(); \
	print(f'Active: {row[0]}'); \
	print(f'Deployed: {row[1]}'); \
	conn.close() if conn else None"

# ── Run tests only ---------------------
test:
	dbt test $(DBT_ARGS)

# -- Clean slate ------------------------------
# just for a clean start for this technical assessment purpose only
# otherwise it is a bad practice to make it which can remove 
# data tables easily.
 
clean:
	@python -c "import duckdb; \
	conn = duckdb.connect('$(DB_PATH)'); \
	conn.execute('DROP SCHEMA IF EXISTS prod_blue CASCADE'); \
	conn.execute('DROP SCHEMA IF EXISTS prod_green CASCADE'); \
	conn.execute('DROP SCHEMA IF EXISTS public CASCADE'); \
	conn.close(); \
	print('Dropped prod_blue, prod_green, and public schemas.')"
	dbt clean $(DBT_ARGS)
