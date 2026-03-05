-- Mart layer: Final denormalized invoice ledger for API consumption.

-- Design decisions:
--   

--   Enforced contract: The YAML schema declares exact column names
--   and types. Any drift causes dbt to fail the build.
--
--   Blue Green: A post hook swaps the public.mart_invoice_ledger proxy
--   view to point at this model after a successful build. 
--   The API always
--   reads from the proxy view. API has no concern with swap 
--and which schema (blue or green) to look at.
--
-- Config note:
--   post-hook is defined in mart_invoice_ledger.yml alongside the contract enforce config.

SELECT
        invoice_id,
        customer_id,
        customer_name,
        customer_country,
        customer_segment,
        customer_email,
        invoice_amount,
        invoice_status,
        invoice_date,
        invoice_due_date,
        payment_terms_days,
        line_item_count,
        calculated_invoice_total,
        amount_discrepancy
        
FROM {{ ref('int_invoice_totals') }}