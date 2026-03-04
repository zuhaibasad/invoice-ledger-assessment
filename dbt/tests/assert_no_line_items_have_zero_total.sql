
-- checks if line_item or product are not present but the invoice got amount in it


select
    invoice_id,
    line_item_count,
    invoice_total
from {{ ref('mart_invoice_ledger') }}
where line_item_count = 0
  and invoice_amount != 0.00
