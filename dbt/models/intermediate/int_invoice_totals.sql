
-- Design decisions:
--
--   LEFT JOINs are used under the assumptions that Draft invoices have no line items yet. INNER JOIN
--   would silently drop them. LEFT JOIN preserves every invoice.
--
--   Invoices with no line items get NULL from the LEFT JOIN but 
--  COALESCE converts these to deterministic defaults (0 and 0.00).

    
WITH invoices AS (
    SELECT * FROM {{ ref('stg_invoices') }}
    
),

customers AS (
    SELECT * FROM {{ ref('stg_customers') }}
),

line_totals AS (
    SELECT
            invoice_id,
            COUNT(line_item_id) AS line_item_count,
            SUM(quantity * unit_price) AS calculated_invoice_total
    FROM {{ ref('stg_invoice_line_items') }}
    GROUP BY invoice_id
)

SELECT
    i.invoice_id,
    i.customer_id,
    c.customer_name,
    c.customer_country,
    c.customer_segment,
    c.customer_email,
    i.invoice_amount,
    i.invoice_status,
    i.invoice_date,
    i.invoice_due_date,
    DATEDIFF('day', i.invoice_date, i.invoice_due_date) AS payment_terms_days,
    COALESCE(lt.line_item_count, 0) AS line_item_count, -- avoid nulls for invoices without line items
    COALESCE(lt.calculated_invoice_total, 0.0) AS calculated_invoice_total, -- avoid nulls for invoices without line items
    i.invoice_amount - COALESCE(lt.calculated_invoice_total, 0.0) AS amount_discrepancy
FROM invoices i 
    LEFT JOIN customers c ON i.customer_id = c.customer_id -- LEFT JOIN makes sure that we dont drop invoices that shoud be there but got no customers assigned
    LEFT JOIN line_totals lt ON i.invoice_id  = lt.invoice_id -- this LEFT JOIN makes sure that we dont skip invoices without line_items like draft invoices or other type