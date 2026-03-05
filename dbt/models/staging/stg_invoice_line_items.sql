



WITH duped_flagged AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY line_item_id, invoice_id ORDER BY line_item_id) AS rn
    FROM {{ source('raw', 'invoice_line_items') }}
)

SELECT
    CAST(line_item_id as bigint) as line_item_id,
    CAST(invoice_id as bigint) as invoice_id,
    NULLIF(TRIM(product_name), '') AS product_name, -- remove unnecessary whitespace and convert empty strings to NULL
    CAST(quantity as int) AS quantity,
    CAST(unit_price AS DOUBLE) AS unit_price
FROM duped_flagged
Where rn=1