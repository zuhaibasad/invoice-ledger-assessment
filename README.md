# Invoice Ledger — Walking Skeleton

A self-contained vertical slice of an Invoice Ledger feature demonstrating clean architecture across a data-intensive stack: **dbt** (DuckDB) → **FastAPI** (Pydantic) → **React** (TypeScript).

This project prioritizes clean boundaries, idempotency, and zero hidden side effects at every layer.

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- [Git](https://git-scm.com/)

### Run the Full Stack

```bash
git clone https://github.com/<your-username>/invoice-ledger.git
cd invoice-ledger
docker compose up --build
```

That's it. One command. Wait for all services to start, then open:

| URL | What You'll See |
|-----|-----------------|
| http://localhost:3000 | Invoice ledger table (React frontend) |
| http://localhost:8000/api/v1/invoices | Raw JSON data (FastAPI endpoint) |
| http://localhost:8000/api/docs | Interactive Swagger documentation |
| http://localhost:8000/api/health | Deployment status and active schema |

### What Happens Behind the Scenes

When `docker compose up` runs, four services execute in sequence:

```
1. data-loader   → Python script loads raw CSVs into DuckDB (raw schema)
                   Exits when done.

2. dbt-runner    → Auto-detects inactive blue/green schema
                   Runs: dbt deps → dbt build --target <inactive>
                   If all models + tests pass → swaps proxy view
                   Exits when done.

3. api           → FastAPI starts on port 8000
                   Reads from public.mart_invoice_ledger (proxy view)
                   Stays running.

4. web           → React dev server starts on port 3000
                   Proxies /api requests to FastAPI
                   Stays running.
```

### Local Development (Without Docker)

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
.venv\Scripts\Activate.ps1   # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Load raw data into DuckDB
cd data
python load_data_into_db.py

# 4. Install dbt packages and build
cd ../dbt
dbt deps --profiles-dir . --project-dir .
make deploy    # auto blue-green deploy

# 5. Start FastAPI
cd ../api
uvicorn main:app --reload --port 8000

# 6. Start React (separate terminal)
cd web
npm install
npm run dev
```

### Makefile Commands

From the project root:

```bash
make dev        # Build into dev schema (safe sandbox)
make deploy     # Auto blue-green deploy (detects inactive color, builds, swaps)
make status     # Show which color is active and when it was deployed
make test       # Run dbt tests only
make clean      # Drop blue + green schemas (fresh start)
```

### Running Tests

```bash
# dbt tests (run during make deploy, or independently)
cd dbt && dbt test --profiles-dir . --project-dir .

# API tests
cd api && pytest tests/ -v

# Frontend tests
cd web && npm test
```

---

## Architectural Decisions

### Why This Architecture?

The assessment asks for a walking skeleton — the thinnest possible vertical slice that exercises every layer end-to-end. Every architectural decision optimizes for one principle: **each layer has exactly one responsibility, and boundaries between layers are enforced by contracts, not conventions.**

```
Raw Data (Python)
    ↓ source()
dbt Staging (stg_*)         → Clean and normalize. ZERO business logic.
    ↓ ref()
dbt Intermediate (int_*)    → Business calculations. Single source of truth.
    ↓ ref()
dbt Mart (mart_*)           → Denormalized, contracted, versioned output.
    ↓ proxy view
FastAPI (/api/v1/)          → Thin serving layer. Pydantic validates. Read-only.
    ↓ typed fetch
React/TypeScript            → Pure presentation. Zero data manipulation.
```

---

### Data Layer: dbt Three-Layer Structure

#### Staging Layer (`stg_*`)

Staging models are 1:1 mirrors of raw source tables. They read from `source()` (not `ref()`) because the raw data is loaded by an external Python script, not managed by dbt. This boundary is explicit and intentional.

Staging models do exactly three things: rename columns for consistency, cast data types explicitly, and normalize values (e.g., `lower(trim(status))`). They perform zero business logic and zero joins.

**Why this matters:** If the upstream source system changes its column names or date formats, only the staging model needs to change. Every downstream model is protected from source-level changes.

**Why `source()` instead of `ref()`:** The raw data is loaded by an external Python script into the `raw` schema. Using `source()` declares this boundary — dbt reads from these tables but never writes to them. This keeps the ingestion concern completely separate from the transformation concern.

#### Intermediate Layer (`int_*`)

Intermediate models contain all business logic. `int_invoice_line_totals` computes `quantity × unit_price` for each line item. `int_invoice_totals` aggregates line totals per invoice using `SUM` and `COUNT`.

These are two separate models rather than one combined query because each has a single responsibility. `int_invoice_line_totals` is the single source of truth for per-line amounts — no other model in the project recalculates `quantity × unit_price`. If a second mart later needs line-level detail, `int_invoice_line_totals` is already available.

**Why business logic lives here, not in FastAPI:** The assessment states "logic should reside in the appropriate layer." A `quantity × unit_price` calculation is a data transformation — it belongs in dbt, where it can be tested, versioned, and reused. Putting it in the API would mean duplicating logic and testing it in two places.

#### Mart Layer (`mart_*`)

The mart is the only model that external consumers query. It joins invoice headers, aggregated totals, and customer data into a single denormalized table.

**Why LEFT JOIN:** Draft invoices may have no line items yet. An INNER JOIN would silently drop them from the result. LEFT JOIN preserves every invoice regardless of line item status.

**Why COALESCE:** When a LEFT JOIN finds no matching line items, it produces NULL for `line_item_count` and `invoice_total`. COALESCE converts these to deterministic defaults (0 and 0.00), ensuring the API never returns NULL for numeric fields that the Pydantic contract declares as non-nullable.

**Enforced contract:** The mart has `contract: { enforced: true }` in its YAML configuration. This means dbt validates that the model's SQL output matches the declared column names and data types at build time. If someone changes the SQL and the output shape drifts, `dbt run` fails — before bad data ever reaches the database.

**Check constraints:** `line_item_count >= 0` and `invoice_total >= 0` are enforced at the database level via `check` constraints. Unlike tests (which catch problems after the fact), constraints prevent invalid data from being materialized in the first place.

---

### Blue-Green Deployment Strategy

#### The Problem

When dbt rebuilds the mart table, there's a window where the data is being replaced. During this window, the API could read stale data, partial data, or encounter an error. This is downtime.

#### The Solution

The project maintains two production schemas: `prod_blue` and `prod_green`. At any given time, one is "active" (serving the API) and the other is "inactive" (available for the next deployment).

```
invoice_warehouse.duckdb
├── raw           ← Python loader writes here (never touched by dbt)
├── prod_blue     ← dbt builds here OR here (alternating)
├── prod_green    ← dbt builds here OR here (alternating)
└── public
    ├── mart_invoice_ledger    ← VIEW pointing to active schema
    └── deployment_state       ← tracks which color is active
```

#### How It Works

1. `make deploy` (or the Docker entrypoint) queries `public.deployment_state` to determine which schema is currently active.
2. It picks the inactive schema as the dbt target.
3. `dbt build --target <inactive>` runs all models and tests in the inactive schema.
4. The `on-run-end` hook (`swap_on_success` macro) inspects the results:
   - If ALL models and tests passed: swaps the proxy view to point at the newly built schema and updates `deployment_state`.
   - If ANY model or test failed: does nothing. The proxy view continues pointing at the previous active schema. The API is unaffected.

**Why the swap is in `on-run-end`, not a dbt model:** dbt models execute before tests. If the proxy view were a model, it would swap before test results are known. The `on-run-end` hook executes after all tests complete, making it the only safe place for the swap.

**Why `CREATE OR REPLACE TABLE` for deployment_state:** A `DELETE` followed by `INSERT` has a crash-vulnerable gap where the table is empty. `CREATE OR REPLACE TABLE ... AS SELECT` is a single atomic DDL statement — either the old state exists or the new state exists, never an empty table.

#### The API Is Color-Blind

FastAPI always queries `public.mart_invoice_ledger` — the proxy view. It has zero knowledge of `prod_blue` or `prod_green`. The deployment strategy is entirely a data layer concern. The API never needs to be redeployed, reconfigured, or restarted when a blue-green swap occurs.

The health endpoint reads `public.deployment_state` for observability, but this is a read operation — the API never writes deployment state.

---

### Backend: FastAPI as a Contract Layer

#### Design Principle

FastAPI is a thin serving layer. It does three things: connects to DuckDB (read-only), queries the mart proxy view, and validates every row through the Pydantic contract. It performs zero business logic, zero data transformation, and zero writes.

#### The Pydantic Contract

The Pydantic models in `contracts/v1/v1.py` form a rigid contract between the dbt mart and the API consumer. Every field maps 1:1 to a column in `mart_invoice_ledger_v1`.

The contract enforces: data types (int, float, date, str), nullability (`customer_email: str | None`), value constraints (`line_item_count: int = Field(ge=0)`), and allowed values (`InvoiceStatus` enum restricts status to a known set).

If the dbt mart somehow produces data that doesn't match this contract — a negative total, an unknown status, a wrong type — Pydantic rejects it at serialization time. The API returns a 500 error rather than silently serving invalid data. This is intentional: contract drift should fail loudly.

#### Explicit SELECT List

The SQL query in the endpoint names every column explicitly rather than using `SELECT *`. This acts as a secondary guard: if dbt adds a new column to the mart, it doesn't leak through the API. Only contracted fields are returned.

#### Why `fetchall()` Instead of `fetchdf()`

Pandas' `fetchdf()` converts SQL NULL values to `NaN` (a float). Pydantic then rejects `NaN` for string fields like `customer_email`. Using DuckDB's native `fetchall()` preserves NULLs as Python `None`, which Pydantic handles correctly for `str | None` fields.

#### Versioned Routing

The endpoint is mounted at `/api/v1/invoices`. If a breaking change is needed, a new version is created:

```
/api/v1/invoices → reads mart_invoice_ledger_v1 → contracts/v1/v1.py
/api/v2/invoices → reads mart_invoice_ledger_v2 → contracts/v2/v2.py
```

Adding v2 is one line in `main.py`: `app.include_router(v2_router, prefix="/api/v2")`. The v1 endpoint remains untouched — zero downtime for existing consumers.

---

### Frontend: React as Pure Presentation

#### Design Principle

The React frontend has zero business logic. It fetches typed data from the API, handles three possible states (loading, error, success), and renders a table. No calculations, no filtering, no data transformation.

#### TypeScript Types Mirror the Pydantic Contract

The `InvoiceLedgerEntry` interface in `types/invoice.ts` mirrors the Pydantic model field by field. The field names, types, and nullability are identical. If these types drift from the Pydantic contract, the TypeScript compiler catches it.

#### Discriminated Union for State Management

The `useInvoices` hook returns a discriminated union:

```typescript
type InvoiceState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: InvoiceLedgerResponse };
```

The component can never be in an ambiguous state. TypeScript forces exhaustive handling of all three cases — you cannot access `data` without first checking that `status === "success"`.

#### AbortController for Cleanup

The hook uses `AbortController` to cancel in-flight fetch requests when the component unmounts. This prevents state updates on unmounted components — a common source of memory leaks and React warnings.

---

### The Triple Contract Chain

Data integrity is enforced at every boundary by a different mechanism:

```
dbt enforced contract    → Column names + types validated at build time
dbt check constraints    → Non-negative values enforced at materialization
Pydantic response model  → Every row validated at serialization time
TypeScript interface     → Type safety enforced at compile time
```

If any layer drifts from the expected shape, it fails at that layer — never silently downstream. A column type change in dbt breaks the dbt build. A missing field from the API breaks Pydantic validation. A changed field name breaks TypeScript compilation.

---

### Idempotency

Every operation in this system is idempotent:

**dbt:** Running `dbt build` multiple times produces an identical database. Models are rebuilt from scratch (tables via `CREATE OR REPLACE`, views via `CREATE OR REPLACE VIEW`). The blue-green swap is atomic.

**FastAPI:** The endpoint is a pure `GET` with no side effects. No counters, no cache mutations, no logging side effects. Call it 1,000 times — same result.

**React:** The component is a pure function of the data it receives. No local storage writes, no global state mutations. Unmount and remount — same render.

**Blue-green swap:** Running `make deploy` twice simply alternates between blue and green. Each deploy is independent and complete. The proxy view is swapped atomically via `CREATE OR REPLACE VIEW`.

---

### Separation of Concerns

| Layer | Responsibility | Does NOT Do |
|-------|---------------|-------------|
| Python loader | Ingest raw data into DuckDB | Transform, validate, or clean data |
| dbt staging | Clean, cast, normalize | Join tables, calculate amounts, apply business rules |
| dbt intermediate | Business calculations, aggregations | Serve data to consumers, know about the API |
| dbt mart | Denormalize for consumption | Filter at query time, apply API-specific logic |
| dbt macros | Blue-green deployment orchestration | Serve data, know about the frontend |
| FastAPI | Serve and validate contracts | Calculate totals, filter data, write to database |
| React | Present data to users | Fetch logic (hook), data transformation, business rules |

If a developer puts `quantity * unit_price` in the Python API code, that's a bug — it belongs in dbt. If a developer adds a `WHERE` clause in the API endpoint, that's a design smell — filtering belongs in a new mart or a query parameter, not embedded business logic.

---

## Testing Strategy

### dbt Tests (Data Integrity)

| Test Type | What It Catches | Example |
|-----------|----------------|---------|
| **unique** | Duplicate primary keys | `invoice_id` in every layer |
| **not_null** | Missing required values | All IDs, dates, amounts |
| **accepted_values** | Invalid enum values | Status must be draft/sent/paid/overdue/cancelled |
| **relationships** | Broken foreign keys | Line item's invoice_id must exist in invoices |
| **is_non_negative** (custom) | Negative monetary amounts | quantity, unit_price, line_total, invoice_total |
| **check constraints** | Database-level enforcement | line_item_count >= 0, invoice_total >= 0 |
| **Singular: math correctness** | Calculation errors | line_total must equal quantity × unit_price |
| **Singular: aggregation integrity** | Aggregation bugs | Mart total must equal sum of line totals |
| **Singular: COALESCE correctness** | LEFT JOIN defaults | Zero-item invoices must have zero total |
| **Singular: date invariant** | Invalid dates | due_date must not be before issued_date |
| **Singular: join integrity** | Orphaned records | Every invoice must have a valid customer |
| **Contract enforcement** | Schema drift | Column names + types validated at build time |

### API Tests (Contract Enforcement)

| Test | What It Validates |
|------|------------------|
| Contract accepts valid data | All field types, nullable handling, zero amounts |
| Contract rejects invalid status | Unknown status values are rejected |
| Contract rejects negative amounts | Negative invoice_amount and calculated_total rejected |
| Contract rejects missing fields | Required fields must be present |
| Endpoint returns 200 | Full request/response cycle works |
| Response envelope structure | data, count, version fields present |
| Count matches data length | No hidden discrepancies |
| All contracted fields present | No missing or extra fields |
| Statuses are lowercase | Staging normalization is working |
| Totals are non-negative | Constraint enforcement through the stack |
| Endpoint is idempotent | Identical calls return identical results |
| Results are ordered | ORDER BY is working |

### Frontend Tests (Component Behavior)

| Test | What It Validates |
|------|------------------|
| Loading state renders | Shows loading indicator before data arrives |
| Success state renders data | Customer names, amounts displayed correctly |
| Null fields display as dash | Graceful handling of nullable fields |
| API error handled | Shows error message on non-200 response |
| Network error handled | Shows error message on fetch failure |
| Currency formatting | Amounts displayed as $1,850.00 not 1850 |
| Status badges render | Status text displayed with correct styling |

---

## Edge Cases in Mock Data

| Scenario | What It Tests |
|----------|--------------|
| Inconsistent status casing (PAID, Paid, paid) | Staging normalization via lower(trim()) |
| Missing customer email | Nullable handling through all layers |
| Zero-quantity line item | Math doesn't produce errors (0 × price = 0.00) |
| Zero unit price | Non-negative constraint still passes |
| Invoice with no line items (draft) | LEFT JOIN + COALESCE defaults to 0 |
| Cancelled invoice | Included in ledger, not silently filtered |
| Same customer, multiple invoices | Aggregation is per-invoice, not per-customer |
| Amount discrepancy between header and lines | Tracked explicitly, not hidden |

---

## Project Structure

```
invoice_ledger/
├── docker-compose.yml              # One command: docker compose up --build
├── Makefile                        # make dev / make deploy / make status
├── requirements.txt                # Python dependencies
├── README.md
│
├── data/
│   ├── load_data_into_db.py        # Loads raw CSVs into DuckDB raw schema
│   ├── raw_sample_data/            # Raw CSV files
│   └── invoice_warehouse.duckdb    # Generated — not committed
│
├── dbt/
│   ├── dbt_project.yml             # on-run-end: swap_on_success(results)
│   ├── profiles.yml                # dev + blue + green targets
│   ├── packages.yml                # dbt_utils dependency
│   ├── models/
│   │   ├── staging/                # source() based, 1:1 mirrors
│   │   ├── intermediate/           # Business calculations
│   │   └── mart/                   # Contracted, versioned output
│   ├── tests/                      # Singular + generic tests
│   └── macros/
│       └── swap_on_success.sql     # Blue-green swap (only if all pass)
│
├── api/
│   ├── main.py                     # App entry, versioned routers, health
│   ├── config.py                   # pydantic-settings configuration
│   ├── database.py                 # Read-only DuckDB connection
│   ├── contracts/v1/v1.py          # Pydantic models (the rigid contract)
│   ├── routers/v1/invoices.py      # GET /api/v1/invoices
│   └── tests/                      # Contract + integration tests
│
├── web/
│   └── src/
│       ├── types/invoice.ts        # TypeScript types mirroring Pydantic
│       ├── hooks/useInvoices.ts    # Typed fetch with discriminated unions
│       ├── components/             # Pure presentation components
│       └── __tests__/              # Component tests
│
├── docker/
│   ├── Dockerfile.data-loader
│   ├── Dockerfile.dbt
│   ├── Dockerfile.api
│   ├── Dockerfile.web
│   └── deploy.sh                   # Blue-green detection for Docker
│
└── scripts/
    ├── get_target.py               # Detects inactive color for Makefile
    ├── status.py                   # Shows deployment status
    └── clean.py                    # Drops deployment schemas
```