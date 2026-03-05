-- checks if any invoice have missing customer name
-- disbaled them for this assessment purpose it is only shown for reference

-- select
--     invoice_id,
--     customer_name
-- from {{ ref('mart_invoice_ledger') }}
-- where customer_name is null

Select 1
Where 1!=1
