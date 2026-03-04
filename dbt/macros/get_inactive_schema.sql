-- Queries public.deployment_state to find which color is currently
-- active then returns the inactive color.
--
-- First deploy handling: If deployment_state doesn't exist yet ie first run creates
-- it and defaults to prod_blue as the first active color/schema (prod_blue in warehouse)
--
-- This macro runs at COMPILE TIME via generate_schema_name.
-- The 'execute' guard is placed here so that it only queries the database during
-- dbt run/build & not during dbt parse or compile.

{% macro get_inactive_schema() %}

    {% if execute %}

        {# Ensure state infrastructure exists on first-ever deploy #}
        {% do run_query("create schema if not exists public") %}
        {% do run_query("
            create table if not exists public.deployment_state (
                active_schema   varchar not null,
                deployed_at     timestamp not null
            )
        ") %}

        {% set result = run_query("select active_schema from public.deployment_state order by deployed_at desc limit 1") %}

        {% if result.rows | length > 0 %}
            {% set active = result.rows[0][0] %}
            {% if active == 'prod_blue' %}
                {{ return('prod_green') }}
            {% else %}
                {{ return('prod_blue') }}
            {% endif %}
        {% else %}
            {# No deployments yet — start with blue #}
            {{ return('prod_blue') }}
        {% endif %}

    {% else %}

        {{ return('prod_blue') }}
    {% endif %}

{% endmacro %}
