-- checks if any invoice have missing customer name

select
    invoice_id,
    customer_name
from {{ ref('mart_invoice_ledger') }}
where customer_name is null
