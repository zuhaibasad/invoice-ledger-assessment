


WITH duped_flagged AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY invoice_id ORDER BY invoice_id) AS rn
    FROM {{ source('raw', 'invoices') }}
)

SELECT
    CAST(invoice_id as bigint) as invoice_id,
    CAST(customer_id as bigint) as customer_id,
    CAST(amount AS DOUBLE) AS invoice_amount,
    COALESCE(TRIM(LOWER(status)), 'unknown') AS invoice_status,
    invoice_date,
    due_date as invoice_due_date    
FROM duped_flagged
Where rn = 1 -- keep only the first occurrence of each invoice_id