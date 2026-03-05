
-- checks if line_item or product are not present but the invoice got amount in it
-- disbaled them for this assessment purpose it is only shown for reference

-- select
--     invoice_id,
--     line_item_count,
--     invoice_amount
-- from {{ ref('mart_invoice_ledger') }}
-- where line_item_count = 0
--   and invoice_amount != 0.00
Select 1
Where 1!=1