# ScriptRunner Behaviours in jira_audit

## What the script does

The audit discovers ScriptRunner-style tables (profile + detail + mapping) under any `ao_*` prefix and returns behaviours that apply to the given project by:

- Matching **mapping** tables: `DETAIL_ID`/`TEMPLATE_ID` + `PROJECT_ID`/`PROJECT_KEY`, or context-style `TEMPLATE_DETAIL_ID` + `TYPE`/`VALUE` (TYPE=1 project key, TYPE=2 project id).
- Matching **detail** table: `PROJECT_KEY` or `TARGET_PROJECT` = project key.

Tables used when present: `ao_33a75d_it_profile`, `ao_33a75d_it_detail`, `ao_33a75d_it_default` (TEMPLATE_ID + PROJECT_ID), `ao_33a75d_it_context` (TEMPLATE_DETAIL_ID + TYPE + VALUE), and any other discovered mapping table.

## If you still see 0 ScriptRunner Behaviours

On **PRD** for project **UAT1ESX** we observed:

- **ao_33a75d_it_m_workflows** has **0 rows** (empty).
- **ao_33a75d_it_default** has no row with `PROJECT_ID = 72343` (UAT1ESX).
- **ao_33a75d_it_detail** has no row with `PROJECT_KEY = 'UAT1ESX'` or `TARGET_PROJECT = 'UAT1ESX'`.
- **ao_33a75d_it_context** has no row with `VALUE = '72343'` or `'UAT1ESX'`.
- The behaviour names from the UI (e.g. "Making RCCA Required...", "Make Build Numeric Field...", "Hide Unhide Local Metadata...") were **not** found in **ao_33a75d_it_profile** (names there are different).

So for this instance/project, the three behaviours shown in the ScriptRunner UI are either:

1. Stored by a **different plugin** (different `ao_*` app key), or  
2. Loaded from a **different source** (e.g. REST API, file, or different DB schema), or  
3. Stored under different column/table names than the ones we query.

## Diagnostics

- **Debug discovery and queries**  
  `JIRA_AUDIT_DEBUG=1 python jira_audit.py --instance PRD --project UAT1ESX 2>&1`  
  This prints how many prefix(s) were found, which profile/detail/mapping tables are used, and when a query returns 0 rows.

- **Explore schema**  
  `python sr_schema_discover.py --instance PRD --project UAT1ESX`  
  This lists `ao_*` tables, searches for behaviour-like names, and tries sample joins.

If you find the correct plugin/tables for your ScriptRunner Behaviours (e.g. another `ao_*` prefix or different column names), the discovery logic in `jira_audit.py` can be extended to use them.
