# Invoice Ledger — Codebase Context for Review

## What This Project Is

A paid technical assessment for a Senior Fullstack Engineer role. The task is to build a self-contained "Invoice Ledger" walking skeleton demonstrating clean architecture across: **dbt (DuckDB) → FastAPI (Pydantic) → React (TypeScript)**.

## What The Reviewer (EJ) Will Evaluate

1. **Clean boundaries** — each layer does ONE thing. dbt handles transformation, FastAPI is a thin contract layer, React is pure presentation.
2. **Idempotency** — running any operation multiple times produces identical results with no side effects.
3. **Zero hidden side effects** — every function does exactly what its name says. No mutations hidden inside reads.
4. **Code clarity** — "code is written for humans to read and machines to execute." Self-documenting names, no clever one-liners.
5. **The "why"** — the README must explain every architectural decision from first principles.

## Architecture Overview

```
Raw Data (Python loader) → raw schema in DuckDB
    ↓
dbt Staging (stg_*)      → clean, cast, normalize. NO business logic.
    ↓
dbt Intermediate (int_*) → calculations, aggregations. Business logic lives here.
    ↓
dbt Mart (mart_*)        → final denormalized view. Enforced contract + versioned.
    ↓
Blue-Green Deployment    → proxy view in public schema. API reads from here.
    ↓
FastAPI (/api/v1/)       → Pydantic contract validates every row. Read-only.
    ↓
React/TypeScript         → typed fetch, pure presentation. Zero data manipulation.
```

## Blue-Green Deployment Strategy

- Three schemas: `dev`, `prod_blue`, `prod_green`
- Raw data lives in `raw` schema (loaded by Python script, not dbt)
- `make deploy` auto-detects which color is active, deploys to the inactive one
- dbt's `on-run-end` hook (`swap_on_success` macro) swaps the `public.mart_invoice_ledger` proxy view ONLY if all models + tests pass
- If any test fails, the swap does NOT happen — API keeps serving the previous good data
- `public.deployment_state` table tracks which color is active (atomic CREATE OR REPLACE, no DELETE+INSERT)
- FastAPI always reads from `public.mart_invoice_ledger` — completely color-blind

## The Triple Contract Chain

```
dbt enforced contract  → "The mart WILL have this shape and these types"
Pydantic response model → "The API WILL return this exact JSON structure"
TypeScript interface    → "The frontend WILL expect this exact type"
```

If any layer drifts, it fails LOUDLY at that layer, never silently downstream.

## Project Structure

```
invoice_ledger/
├── Makefile                        # make dev / make deploy / make status / make clean
├── README.md
│
├── scripts/
│   ├── get_target.py               # Detects inactive blue/green color
│   ├── status.py                   # Shows active deployment state
│   └── clean.py                    # Drops deployment schemas
│
├── data/                           # dbt project
│   ├── dbt_project.yml             # on-run-end: swap_on_success(results)
│   ├── profiles.yml                # dev + blue + green targets
│   ├── macros/
│   │   └── swap_on_success.sql     # Swaps proxy view if all tests pass
│   ├── models/
│   │   ├── staging/                # source() based, 1:1 mirrors of raw tables
│   │   │   ├── _sources.yml        # Declares raw.invoices, raw.customers, raw.invoice_line_items
│   │   │   ├── _staging__models.yml
│   │   │   ├── stg_invoices.sql
│   │   │   ├── stg_invoice_lines.sql
│   │   │   └── stg_customers.sql
│   │   ├── intermediate/           # Business calculations
│   │   │   ├── _intermediate__models.yml
│   │   │   ├── int_invoice_line_totals.sql
│   │   │   └── int_invoice_totals.sql
│   │   └── mart/                   # Contracted, versioned output
│   │       ├── _mart__models.yml   # enforced contract + check constraints
│   │       └── mart_invoice_ledger.sql
│   └── tests/
│       ├── generic/
│       │   └── is_non_negative.sql
│       ├── assert_line_total_equals_quantity_times_price.sql
│       ├── assert_mart_total_matches_line_sum.sql
│       ├── assert_no_line_items_have_zero_total.sql
│       ├── assert_due_date_not_before_issued_date.sql
│       └── assert_all_invoices_have_customer.sql
│
├── api/                            # FastAPI backend
│   ├── config.py                   # pydantic-settings, LEDGER_ env prefix
│   ├── database.py                 # Read-only DuckDB connection
│   ├── main.py                     # App entry, CORS, versioned routers, health endpoint
│   ├── contracts/
│   │   └── v1/
│   │       └── v1.py               # Pydantic models — the rigid contract
│   ├── routers/
│   │   └── v1/
│   │       └── invoices.py         # GET /api/v1/invoices — reads public proxy view
│   └── tests/
│       ├── test_contracts.py       # Unit: Pydantic accepts/rejects correctly
│       └── test_invoices.py        # Integration: full endpoint validation
│
└── web/                            # React frontend
    ├── vite.config.ts              # Proxy /api → localhost:8000
    ├── tsconfig.json               # strict: true
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── types/
        │   └── invoice.ts          # TypeScript interfaces mirroring Pydantic
        ├── hooks/
        │   └── useInvoices.ts      # Typed fetch with discriminated union states
        ├── components/
        │   └── InvoiceLedger.tsx    # Pure presentation, zero business logic
        └── __tests__/
            └── InvoiceLedger.test.tsx
```

## Key Design Decisions

### Why source() not ref() in staging?
Raw data is loaded by an external Python script, not by dbt seeds. `source()` declares this boundary explicitly — dbt reads from raw tables but never writes to them.

### Why LEFT JOIN + COALESCE in the mart?
Draft invoices have no line items. INNER JOIN would silently drop them. LEFT JOIN preserves every invoice. COALESCE converts NULLs to deterministic defaults (0 and 0.00).

### Why explicit SELECT list in the API query?
If dbt adds a column to the mart, it doesn't leak through the API. Only contracted fields are returned. This is a secondary guard on top of Pydantic validation.

### Why fetchall() instead of fetchdf() in the endpoint?
Pandas converts SQL NULLs to NaN (a float). Pydantic rejects NaN for string fields. Using fetchall() preserves NULLs as Python None, which Pydantic handles correctly.

### Why discriminated union in useInvoices hook?
The component never has to guess its state. `status: "loading" | "error" | "success"` forces exhaustive handling of all three cases in the component.

### Why is the proxy view NOT a dbt model?
Models execute BEFORE tests. If the proxy view were a model, it would swap before we know the data is good. The on-run-end hook executes AFTER all tests pass, making it the only safe place for the swap.

### Why atomic CREATE OR REPLACE for deployment_state?
DELETE + INSERT has a crash-vulnerable gap where the table is empty. CREATE OR REPLACE TABLE ... AS SELECT is a single atomic DDL — either the old state exists or the new state exists, never an empty table.

## Testing Strategy

### dbt Tests
- Schema tests: unique, not_null, accepted_values, relationships, is_non_negative
- Contract enforcement: column names + types validated at build time
- Check constraints: line_item_count >= 0, invoice_total >= 0 at materialization
- Singular tests: math correctness, aggregation integrity, COALESCE logic, date invariants, join integrity

### API Tests
- Contract unit tests: Pydantic accepts valid data, rejects invalid shapes, handles nullables
- Integration tests: endpoint returns 200, envelope structure, field completeness, idempotency, ordering

### Frontend Tests
- Loading state renders
- Success state renders data
- Null fields display as "—"
- API errors handled
- Network errors handled
- Currency formatting correct

## How To Run

```bash
# 1. Load raw data
python scripts/load_data.py

# 2. dbt build (dev)
make dev

# 3. Blue-green deploy
make deploy

# 4. Start API
cd api && uvicorn main:app --reload --port 8000

# 5. Start frontend
cd web && npm run dev

# 6. Run tests
cd api && pytest tests/ -v
cd web && npm test
```

## What To Review

When reviewing this codebase, please check:
1. Do the dbt layers have clean separation? (staging = no logic, intermediate = calculations, mart = joins only)
2. Does the Pydantic contract match the dbt mart schema exactly?
3. Do the TypeScript types match the Pydantic contract exactly?
4. Is the API truly a thin serving layer with zero business logic?
5. Is the blue-green swap mechanism safe? (only swaps after all tests pass)
6. Are there any hidden side effects in any layer?
7. Is every operation idempotent?
8. Are the tests testing the RIGHT things at the RIGHT layer?
