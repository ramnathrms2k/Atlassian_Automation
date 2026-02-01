# Jira Project Config Audit – Enhancement Plan (Post–JSON Review)

## Feedback summary

The JSON export is ~85% of the way to a total reconstruction or high-fidelity comparison. The following “environmental” pieces were called out as missing for a perfect clone or deep forensic review.

---

## Gap vs current implementation

| Feedback gap | Current state | Feasibility |
|--------------|---------------|-------------|
| **1. Issue type scheme contents** | We have `issue_type_scheme` (name only). | **Easy** – Add list of all issue types in the scheme (including 0-issue types) from `issuetypescreenschemeentity` (or `issuetypescheme`). |
| **2. Workflow scheme mapping** | We **already have** it: `workflow_scheme_details.workflows[]` has `workflow_name` + `issue_types[]`. | **Trivial** – Add a flat `workflow_scheme_mapping: [{ issue_type, workflow_name }, ...]` and surface it in summary so “which issue type → which workflow” is explicit. |
| **3. Field option values (dropdowns)** | We have `custom_field_options` (cfname, customvalue) from `fetch_cf_options`. | **Easy** – Add `field_id` (e.g. customfield_43231) and `option_id` to each row so “Option IDs for VCF Category” is explicit. |
| **4. Versions / Releases** | We have `version_count` only. | **Easy** – Add `versions: [{ id, name, released, archived }]` from `projectversion`. |
| **5. Components** | We have `component_count` only. | **Easy** – Add `components: [{ id, name, lead, description }]` from `component`. |
| **6. Field configuration (hidden/shown, renderer)** | Not present. | **Medium** – Needs fieldconfigscheme + fieldconfigitem (and possibly fieldlayout). Defer to Phase 2. |
| **7. Agile boards (JQL, columns, swimlanes)** | Not present. | **Larger** – Different tables/plugins. Defer. |
| **8. Webhooks / Mail handlers** | Not present. | **Out of scope** for this audit; optional later. |

---

## Recommended Phase 1 (simple extension, low hassle)

Implement only items that are **easy** or **trivial** and do not change existing behaviour:

1. **Issue types in scheme**  
   - New key: `issue_type_scheme_issue_types` (list of issue type names, and optionally IDs).  
   - Query: distinct issue types from the project’s issue type (screen) scheme so “hidden” types with 0 issues are visible.  
   - Summary: add a short “Issue types in scheme” list (text + HTML).

2. **Explicit workflow mapping**  
   - New key: `workflow_scheme_mapping` (list of `{ issue_type, workflow_name }`).  
   - Derived from existing `workflow_scheme_details` (no new DB query).  
   - Summary: add a small “Issue type → Workflow” table so admins can confirm “which issue types use PR Bug Workflow” at a glance.

3. **Versions list**  
   - New key: `versions` (list of `{ id, name, released, archived }` or similar).  
   - Query: `projectversion` for the project.  
   - Summary: show version list (replace or supplement “Version count” where useful).

4. **Components list**  
   - New key: `components` (list of `{ id, name, lead, description }` or similar).  
   - Query: `component` for the project.  
   - Summary: show component list (replace or supplement “Component count” where useful).

5. **Custom field options – field_id and option_id**  
   - Extend `fetch_cf_options` (and thus `custom_field_options`) to include:  
     - `field_id` (e.g. `customfield_43231`),  
     - `option_id` where available from `customfieldoption`.  
   - Keeps existing cfname/customvalue; no breaking change.  
   - Summary: ensure table (or export) shows field ID and option ID so “Option IDs for VCF Category” is explicit.

---

## What we are **not** doing in Phase 1

- **Field configuration scheme** (hidden vs shown, renderers) – Phase 2.  
- **Agile boards** (names, JQL, columns, swimlanes) – larger feature.  
- **Webhooks / Mail handlers** – out of scope for this pass.

---

## Rollout (same as before)

1. **Implement and test** in pregit:  
   `/Users/ramanathanm/Downloads/atlassian-automation-pregit-01092026/jira-project-config-audit/`
2. **Copy fixes** into:  
   - `atlassian-automation/jira-project-config-audit/`  
   - `atlassian-automation/Devops/jira-project-config-audit/`  
   - `atlassian-automation/Devops/atlassian-automation/jira-project-config-audit/`
3. **Git**: commit delta, push to both remotes (github.com + GTO/Devops) on the usual branch.

---

## Implementation order (suggested)

1. **workflow_scheme_mapping** (derived, no DB) – quick win.  
2. **versions** and **components** (simple queries, same pattern).  
3. **issue_type_scheme_issue_types** (one new query, similar to existing scheme logic).  
4. **custom_field_options** extension (field_id, option_id).  
5. **Summary text + HTML** for new keys (tables/lists as above).

---

## Open points

- **Issue type scheme source:** Prefer listing issue types from the **Issue Type Screen Scheme** (current scheme we use) vs a separate “Issue Type Scheme” table if your Jira has both; we can align with whatever the project is actually using.  
- **Versions/Components:** If you want to limit payload size for huge projects, we can cap list length (e.g. first 500) and still expose count; default can be “no cap” for now.  
- **Field configuration (hidden/renderer):** Confirmed as Phase 2; not in initial rollout.

If this plan matches what you want, next step is to implement Phase 1 in pregit, then copy and push as above.
