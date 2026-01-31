# Jira Project Config Audit

## Overview

A framework for auditing Jira project configuration from the database and optional ScriptRunner REST API. It produces a full snapshot (workflow scheme details, automation rules, permissions, screens and fields, ScriptRunner behaviours) with a human-readable summary and JSON export. Includes a Flask web UI for single-audit and side-by-side compare.

## What It Does

- **Project metadata**: Lead, schemes, issue counts, last created/updated issue
- **Workflow scheme details**: Steps, transitions, conditions, validators, post-functions; full descriptor XML (expand/collapse in UI)
- **Automation rules**: Name, state, scope, rule owner/actor (with display name and email when resolvable)
- **Permission details**: Scheme permissions with parameter display (user display name/email when type=user)
- **Screens and fields**: Issue type → screen → tab → field with required/optional and scope
- **ScriptRunner behaviours**: Names, descriptions, project/issuetype mapping counts (DB or REST API fallback)
- **Custom field options**: Project-scoped custom field options
- **Compare**: Run two audits (different instances or projects) and view side-by-side

## Prerequisites

- Python 3.8+
- MySQL read-only access to Jira database
- (Optional) ScriptRunner REST API Bearer token for behaviour names when DB has no mapping

## Configuration

### config.ini (sanitized in this copy)

Create or edit `config.ini` with one section per Jira instance. Replace `TOKEN` and host/URL placeholders with your values.

```ini
[DEFAULT]
port = 3306
user = atlassian_readonly
password = TOKEN
database = jiradb
sr_bearer_token = TOKEN

[SBX]
host = db-host-sbx.example.com
jira_base_url = http://jira-host-sbx.example.com:8080

[PRD]
host = db-host-prd.example.com
jira_base_url = https://jira-host-prd.example.com
```

- **password**: Database password (use TOKEN placeholder in shared repos)
- **sr_bearer_token**: ScriptRunner REST API Bearer token (optional; for behaviour name fallback)
- **host**: MySQL host for that instance
- **jira_base_url**: Jira base URL (optional; for ScriptRunner API)

## How to Use

### CLI

```bash
# Install dependencies
pip install -r requirements.txt

# Run audit (JSON to stdout)
python jira_audit.py --instance SBX --project UAT1ESX

# With human-readable summary before JSON
python jira_audit.py --instance SBX --project UAT1ESX --summary
```

### Web UI

```bash
python app.py
# Open http://localhost:9000
# Select instance and project key, run audit; view Summary or JSON; use Compare for two audits.
```

### API

- `GET /api/audit?instance=SBX&project=UAT1ESX` — full audit + summary_html + snapshot JSON
- `GET /api/audit/json?instance=SBX&project=UAT1ESX` — snapshot JSON only
- `GET /api/audit/html?instance=SBX&project=UAT1ESX` — HTML summary only
- `GET /api/compare?instance1=SBX&project1=UAT1ESX&instance2=PRD&project2=UAT1ESX` — side-by-side compare

## Output

- **Summary (text)**: Human-readable sections (metadata, schemes, workflow details, automation rules, behaviours, permissions, screens, custom fields)
- **Summary (HTML)**: Tables with sticky first two columns in workflow tables; expand/collapse descriptor XML per workflow
- **JSON**: Full snapshot for automation or archival; includes workflow conditions/validators/post-functions with class and args

## Files Overview

| File | Purpose |
|------|--------|
| `jira_audit.py` | Core audit: DB queries, workflow XML parsing, user enrichment, summary builders |
| `app.py` | Flask app: UI and API routes |
| `compare_audit.py` | Compare two audits (used by API) |
| `config.ini` | Instance config (host, user, password, jira_base_url, sr_bearer_token) |
| `requirements.txt` | flask, mysql-connector-python |
| `COMPARE_USAGE.md` | How to use compare feature |
| `SR_BEHAVIORS_README.md` | ScriptRunner behaviours discovery |

## Security Notes

- **Credentials**: All passwords and tokens in this copy are sanitized (TOKEN / example.com). Replace with real values locally; do not commit secrets.
- **Database**: Use a read-only database user.
- **ScriptRunner API**: Use a token with minimal required scope.

## Troubleshooting

- **Project not found**: Ensure `config.ini` has the correct host and credentials for the chosen instance.
- **Workflow details empty**: Requires `workflowschemeentity` and `jiraworkflows` tables and readable descriptor XML.
- **Conditions/validators empty in UI**: Parser reads `<arg name="class.name">` from workflow XML; if your Jira uses a different format, conditions may be empty in JSON until parser is extended.

---

**Note**: This is production-ready code. Replace TOKEN and example host/URL placeholders in `config.ini` before running.
