


WITH duped_flagged AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY invoice_id ORDER BY invoice_id) AS rn
    FROM {{ source('raw', 'invoices') }}
)

SELECT
    invoice_id,
    customer_id,
    CAST(amount AS DOUBLE) AS invoice_amount,
    COALESCE(TRIM(LOWER(status)), 'unknown') AS invoice_status,
    invoice_date,
    invoice_due_date    
FROM duped_flagged
Where rn = 1 -- keep only the first occurrence of each invoice_id