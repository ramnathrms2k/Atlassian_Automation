# ScriptRunner Behaviours REST API – curl reference

Use these against your Jira instance (ScriptRunner for Jira Data Center/Server).  
**Auth:** Bearer token works; Basic auth (`-u user:password`) also works per ScriptRunner docs.

## SBX (sandbox)

- **Base URL:** `http://jira-lvnv-it-108.lvn.broadcom.net:8080`
- **Token:** (Bearer) use your personal access token in the header below.

### 1. Get behaviour mappings (project/issue type → behaviour config)

Returns XML: which project IDs and issue types use which behaviour configuration IDs.

```bash
curl -s -H "Authorization: Bearer YOUR_TOKEN" \
  "http://jira-lvnv-it-108.lvn.broadcom.net:8080/rest/scriptrunner/behaviours/latest/config"
```

- **200:** XML `<behaviours>` with `<project pid="...">` and `<issuetype id="..." configuration="UUID"/>`.
- **401:** Invalid or missing auth (e.g. wrong token or user/password).

### 2. Get a single behaviour’s configuration (XML)

Replace `BEHAVIOUR_UUID` with one of the `configuration="..."` UUIDs from step 1.

```bash
curl -s -H "Authorization: Bearer YOUR_TOKEN" \
  "http://jira-lvnv-it-108.lvn.broadcom.net:8080/rest/scriptrunner/behaviours/latest/config/BEHAVIOUR_UUID"
```

### 3. Optional: Basic auth (username:password)

If your instance uses Basic auth instead of a Bearer token:

```bash
curl -s -u "USERNAME:PASSWORD" \
  "http://jira-lvnv-it-108.lvn.broadcom.net:8080/rest/scriptrunner/behaviours/latest/config"
```

## Quick test (Bearer token)

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  "http://jira-lvnv-it-108.lvn.broadcom.net:8080/rest/scriptrunner/behaviours/latest/config" \
  | tail -5
```

- If you see `HTTP_CODE:200` and XML starting with `<behaviours>`, the API and token are working.
- If you see `HTTP_CODE:401`, check the token and Jira user permissions.

## References

- [Migrating Behaviours (ScriptRunner docs)](https://docs.adaptavist.com/sr4js/latest/features/behaviours/migrating-behaviours) – config URL and POST examples.
