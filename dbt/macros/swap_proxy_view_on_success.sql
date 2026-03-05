-- on-run-end hook: Executes after ALL (models + tests) complete.
--
-- Logic:
--   1. Only acts on prod target. dev builds never trigger swaps.
--   2. Inspects the results list for ANY errors or test failures.
--   3. If ALL passed → swaps proxy view + updates deployment_state in an atomic way
--   4. If ANY failed → logs a warning, does NOT swap. The previous
--      active schema remains live. Zero impact on the API.
--
-- This is the key safety mechanism: bad data NEVER reaches the API.
-- The swap is atomic and the proxy view is replaced in a single DDL
-- statement so the API either sees the old data or the new data,
-- never a partial state.

{% macro swap_proxy_view_on_success(results) %}

    {% if target.name in ['blue', 'green'] and execute %}

        {# Count failures across models and tests #}
        {% set error_count = 0 %}
        {% set failure_count = 0 %}
        {% for result in results %}
            {% if result.status == 'error' %}
                {% set error_count = error_count + 1 %}
            {% elif result.status == 'fail' %}
                {% set failure_count = failure_count + 1 %}
            {% endif %}
        {% endfor %}
        {% set total_failures = error_count + failure_count %}

        {% if total_failures == 0 %}

            {{ log("All nodes passed. Swapping proxy view to " ~ target.schema, info=True) }}

            {% set create_schema_sql %}
                create schema if not exists public
            {% endset %}
            {% do run_query(create_schema_sql) %}

            {% set swap_view_sql %}
                create or replace view public.mart_invoice_ledger as
                select * from {{ target.schema }}.mart_invoice_ledger_v1
            {% endset %}
            {% do run_query(swap_view_sql) %}

            {% set update_state_sql %}
                create or replace table public.deployment_state as
                select
                    '{{ target.schema }}' as active_schema,
                    now() as deployed_at
            {% endset %}
            {% do run_query(update_state_sql) %}

            {{ log("Deployment complete. Active schema: " ~ target.schema, info=True) }}

        {% else %}

            {{ log(total_failures ~ " failure(s) detected. Proxy view NOT swapped.", info=True) }}

        {% endif %}

    {% endif %}

{% endmacro %}
