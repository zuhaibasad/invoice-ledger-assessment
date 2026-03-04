
  
  create view "invoice_warehouse"."dev"."stg_invoices__dbt_tmp" as (
    SELECT *
FROM "invoice_warehouse"."raw"."invoices"
  );
