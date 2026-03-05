
WITH duped_flagged AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY customer_id) AS rn
    FROM {{ source('raw', 'customers') }}
)

SELECT
    cast(customer_id as bigint) as customer_id,
    NULLIF(TRIM(customer_name), '') AS customer_name,
    NULLIF(TRIM(UPPER(country)), '') AS customer_country,
    COALESCE(LOWER(TRIM(segment)), 'unknown') AS customer_segment,
    NULLIF(LOWER(TRIM(email)), '') as customer_email
FROM duped_flagged
Where rn=1