-- Controls which schema every model lands in.
--
-- Behavior by target:
--   dev  or any other → all models land in 'dev' schema.
--   prod → all models land in the auto-detected INACTIVE color.
--          The get_inactive_schema() macro queries deployment_state
--          to determine which color to use.
--
-- Developers run 'dbt build --target prod' and the system run everything and swaps schema if everything is successful
-- This makes sure API is served with zero-downtime and only good data gets to the API.

{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- if target.name == 'prod' -%}
        {{ get_inactive_schema() }}
    {%- else -%}
        {{ target.schema }}
    {%- endif -%}

{%- endmacro %}
