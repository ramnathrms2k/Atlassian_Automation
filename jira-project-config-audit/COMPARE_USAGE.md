# Compare and view audits side by side

## What the summary shows

Each audit summary includes **all captured information** in this order:

1. **Project metadata** — Project Key, Project Name, Project Lead, Project Category, Default Assignee Type, Issue Type Scheme, Total Issue Count, Component Count, Version Count, Permission Entries, Last Created Issue, Last Issue Created (timestamp), Last Updated Issue, Last Updated (timestamp)
2. **Issue count by type** — table of issue type name and count (e.g. Bug: 500, Story: 200)
3. **Schemes** — Workflow, Permission, Notification
4. **Automation Rules** — name and state (Enabled/Disabled)
5. **ScriptRunner Behaviors** — name and description
6. **Permission Details** — permission key, type, parameter
7. **Screens and Fields** — issue type, screen, tab, field ID/name, required/optional
8. **Custom Field Options** — field name and value

---

## Start the app

```bash
cd jira-project-config-audit
python app.py
```

Open **http://localhost:9000/** (or your host:9000). Use **Compare** in the nav or go to **http://localhost:9000/compare**.

---

## How to test the Compare feature (explicit steps)

Follow these steps to verify the Compare feature end-to-end.

### Prerequisites

- `config.ini` has at least one instance (e.g. `SBX`, `PRD`) with correct DB credentials.
- You know a valid project key (e.g. `UAT1ESX`) that exists on that instance.

### Test 1: Single audit and summary content

1. Open **http://localhost:9000/** in a browser.
2. In the form, choose **Instance** (e.g. `PRD`) and enter **Project key** (e.g. `UAT1ESX`).
3. Click **Run audit**.
4. **Expected:** The result area appears with a **Summary** tab and a **JSON** tab.
5. On the **Summary** tab, verify from top to bottom:
   - **Project metadata** section shows: Project Key, Project Name, Project Lead, Last Created Issue, Last Issue Created (timestamp). Values should match your project (lead can be a username; last issue key like `UAT1ESX-123`; timestamp in ISO format).
   - **Schemes** table shows Workflow, Permission, Notification scheme names.
   - **Automation Rules** table lists rule names and state.
   - **ScriptRunner Behaviors** (if any), **Permission Details**, **Screens and Fields**, **Custom Field Options** sections follow.
6. Switch to the **JSON** tab and confirm the same data appears in the raw snapshot (e.g. `project_key`, `project_name`, `project_lead`, `last_issue_key`, `last_issue_created`, then schemes, automation_rules, etc.).

### Test 2: Compare — same project, two environments

1. Open **http://localhost:9000/compare**.
2. **Left column:** Select Instance = `SBX`, Project = `UAT1ESX` (or your sandbox instance and project).
3. **Right column:** Select Instance = `PRD`, Project = `UAT1ESX` (same project key, production instance).
4. Click **Run both audits**.
5. **Expected:** Left column shows “Loading left…”, right “Loading right…”, then both columns show the full HTML summary (with Project metadata at top, then Schemes, Automation Rules, etc.) for that instance/project.
6. **Verify:** Scroll each column. Left summary should reflect SBX data (e.g. SBX project lead, last issue, schemes). Right summary should reflect PRD data. Compare sections side by side (e.g. different automation rule counts or scheme names between SBX and PRD).

### Test 3: Compare — single column (Run left / Run right)

1. Stay on **http://localhost:9000/compare**.
2. **Left:** Instance = `PRD`, Project = `UAT1ESX`.
3. **Right:** Leave as-is or clear.
4. Click **Run left** (the left form’s submit button).
5. **Expected:** Only the left column loads and shows the PRD audit summary (Project metadata, Schemes, etc.). Right column stays empty or unchanged.
6. Repeat using **Run right** with Right = `PRD`, `UAT1ESX` and confirm only the right column loads.

### Test 4: Compare — two different projects

1. On the Compare page, set **Left** to Instance A, Project X (e.g. `PRD`, `PROJA`).
2. Set **Right** to Instance B, Project Y (e.g. `PRD`, `PROJB` or another instance).
3. Click **Run both audits**.
4. **Expected:** Left column shows audit for (A, X); right column shows audit for (B, Y). Each summary shows that project’s metadata, schemes, rules, etc. You can compare two different projects or the same project key on two instances.

### Test 5: API compare (optional)

1. In a browser or with `curl`, open:
   `http://localhost:9000/api/compare?instance1=SBX&project1=UAT1ESX&instance2=PRD&project2=UAT1ESX`
2. **Expected:** JSON response with `left` and `right`. Each has `summary_html`, `snapshot`, `instance`, `project`. `snapshot` includes `project_lead`, `last_issue_key`, `last_issue_created`, schemes, automation_rules, etc.

If any step fails (e.g. error message, missing Project metadata, or only one column loading when both should), note the step number and the message/behavior for debugging.

---

## Compare page — step-by-step (reference)

### 1. Same project in two environments (e.g. SBX vs PRD)

- **Left:** Instance = `SBX`, Project = `UAT1ESX` (or your project key).
- **Right:** Instance = `PRD`, Project = `UAT1ESX` (same project key).
- Click **Run both audits**.
- Both columns load the HTML summary (tables) for that instance/project. Scroll each column to compare Schemes, Automation Rules, ScriptRunner Behaviors, Permission Details, Screens and Fields, Custom Field Options.

### 2. Two different projects

- **Left:** Instance and project key for the first project.
- **Right:** Instance and project key for the second project (same or different instance).
- Click **Run both audits** to see both summaries side by side.

### 3. Single column

- Fill only the side you care about (e.g. Left: SBX, UAT1ESX).
- Click **Run left** (or **Run right**) to load that audit in that column only.

---

## API (for scripts or tools)

- **Single audit (JSON + summary):**  
  `GET /api/audit?instance=SBX&project=UAT1ESX`  
  Returns `{ "summary", "summary_html", "snapshot" }`.

- **Compare (both audits):**  
  `GET /api/compare?instance1=SBX&project1=UAT1ESX&instance2=PRD&project2=UAT1ESX`  
  Returns `{ "left": { "summary_html", "snapshot", "instance", "project" }, "right": { ... } }`.

- **Summary only (HTML):**  
  `GET /api/audit/html?instance=SBX&project=UAT1ESX`  
  Returns HTML summary only.

- **Summary only (plain text):**  
  `GET /api/audit/summary?instance=SBX&project=UAT1ESX`  
  Returns plain-text summary.

- **Full JSON only:**  
  `GET /api/audit/json?instance=SBX&project=UAT1ESX`  
  Returns the full audit snapshot as JSON.

---

## CLI comparison (no browser)

To compare two JSON audit files (e.g. from `jira_audit.py`):

```bash
python jira_audit.py --instance PRD --project UAT1ESX > prd_uat1esx.json
python jira_audit.py --instance SBX --project UAT1ESX > sbx_uat1esx.json
python compare_audit.py prd_uat1esx.json sbx_uat1esx.json
```

This prints a short comparison (schemes, automation rule count, ScriptRunner behavior count, etc.) to the terminal.

---

## Snapshot fields (what is captured)

The audit snapshot and summary include:

| Field | Description |
|-------|--------------|
| `project_key` | Jira project key (e.g. UAT1ESX) |
| `project_name` | Project name |
| `project_lead` | Project lead username (from `project.lead`) |
| `project_category` | Project category name (if set) |
| `default_assignee_type` | Default assignee type (e.g. UNASSIGNED, PROJECT_LEAD) |
| `issue_type_scheme` | Name of the issue type (screen) scheme |
| `total_issue_count` | Total number of issues in the project |
| `issue_count_by_type` | List of { issue_type, count } (e.g. Bug: 500, Story: 200) |
| `component_count` | Number of components in the project |
| `version_count` | Number of versions (affects/fix for) in the project |
| `permission_entry_count` | Number of permission entries in the scheme |
| `last_issue_key` | Key of the most recently created issue (e.g. UAT1ESX-123) |
| `last_issue_created` | Created timestamp of that issue (ISO format) |
| `last_updated_issue_key` | Key of the most recently updated issue |
| `last_updated_issue_timestamp` | Updated timestamp of that issue (ISO format) |
| `workflow_scheme` | Workflow scheme name |
| `permission_scheme` | Permission scheme name |
| `notification_scheme` | Notification scheme name |
| `automation_rules` | List of rule name + state |
| `sr_behaviors` / `sr_behaviors_count` | ScriptRunner behaviors and count |
| `permission_details` | Permission key, type, parameter |
| `screens_and_fields` | Issue type, screen, tab, field ID/name, required/optional |
| `custom_field_options` | Custom field name and value |
