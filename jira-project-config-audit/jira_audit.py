import mysql.connector
import configparser
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from decimal import Decimal
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

DEBUG = os.environ.get('JIRA_AUDIT_DEBUG', '').strip() in ('1', 'true', 'yes')

# Helper for JSON serialization of database numbers
def json_serial(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return str(obj)


def _format_user_display(user_id, display_name, email):
    """Format user for summary: 'Display Name / email' when both present, else user_id."""
    if display_name and email:
        return f"{display_name} / {email}"
    if display_name:
        return f"{display_name}" + (f" / {email}" if email else "")
    if email:
        return (user_id or "—") + f" / {email}"
    return user_id if user_id else "—"


def _format_projectrole_display(role_id, role_name):
    """Format project role for summary: 'id / role_name' when name present, else id (consistent with user display)."""
    if role_name and str(role_name).strip():
        return f"{role_id} / {role_name.strip()}"
    return str(role_id) if role_id is not None else "—"


def get_args():
    parser = argparse.ArgumentParser(description="Jira Master Audit Tool v6.8")
    parser.add_argument("--instance", required=True, help="Instance name from config.ini")
    parser.add_argument("--project", required=True, help="Jira Project Key (e.g., UAT1ESX)")
    parser.add_argument("--summary", action="store_true", help="Print human-readable summary before JSON")
    return parser.parse_args()


def build_audit_summary(snapshot):
    """
    Build a human-readable summary: object category and object names for admin readability.
    Includes project metadata (lead, last created issue) and all captured config. Returns a string.
    """
    lines = []
    key = snapshot.get("project_key", "")
    name = snapshot.get("project_name", "")
    lines.append("=" * 60)
    lines.append(f"JIRA PROJECT CONFIG SUMMARY — {key} ({name})")
    lines.append("=" * 60)

    # Project metadata (all captured fields)
    lines.append("\n--- Project metadata ---")
    lines.append(f"Project Key: {key}")
    lines.append(f"Project Name: {name}")
    lead = snapshot.get("project_lead")
    lead_dn = snapshot.get("project_lead_display_name")
    lead_em = snapshot.get("project_lead_email")
    lead_display = _format_user_display(lead, lead_dn, lead_em)
    lines.append(f"Project Lead: {lead_display}")
    cat = snapshot.get("project_category")
    lines.append(f"Project Category: {cat if cat else '—'}")
    assignee_type = snapshot.get("default_assignee_type")
    lines.append(f"Default Assignee Type: {assignee_type if assignee_type else '—'}")
    its = snapshot.get("issue_type_scheme")
    lines.append(f"Issue Type Scheme: {its if its else '—'}")
    it_list = snapshot.get("issue_type_scheme_issue_types") or []
    if it_list:
        lines.append(f"Issue types in scheme ({len(it_list)}): {', '.join(it_list)}")
    total = snapshot.get("total_issue_count")
    lines.append(f"Total Issue Count: {total if total is not None else '—'}")
    comp = snapshot.get("component_count")
    lines.append(f"Component Count: {comp if comp is not None else '—'}")
    ver = snapshot.get("version_count")
    lines.append(f"Version Count: {ver if ver is not None else '—'}")
    versions = snapshot.get("versions") or []
    if versions:
        lines.append(f"\nVersions ({len(versions)}):")
        for v in versions:
            name = v.get("name") or "—"
            rel = "released" if v.get("released") else "unreleased"
            arch = "archived" if v.get("archived") else ""
            lines.append(f"  • {name} ({rel}" + (f", {arch}" if arch else "") + ")")
    components = snapshot.get("components") or []
    if components:
        lines.append(f"\nComponents ({len(components)}):")
        for c in components:
            name = c.get("name") or "—"
            lead = c.get("lead") or ""
            lines.append(f"  • {name}" + (f" (lead: {lead})" if lead else ""))
    perm_count = snapshot.get("permission_entry_count")
    lines.append(f"Permission Entries: {perm_count if perm_count is not None else '—'}")
    last_key = snapshot.get("last_issue_key")
    last_created = snapshot.get("last_issue_created")
    lines.append(f"Last Created Issue: {last_key if last_key else '—'}")
    lines.append(f"Last Issue Created (timestamp): {last_created if last_created else '—'}")
    last_up_key = snapshot.get("last_updated_issue_key")
    last_up_ts = snapshot.get("last_updated_issue_timestamp")
    lines.append(f"Last Updated Issue: {last_up_key if last_up_key else '—'}")
    lines.append(f"Last Updated (timestamp): {last_up_ts if last_up_ts else '—'}")
    by_type = snapshot.get("issue_count_by_type") or []
    if by_type:
        lines.append("\nIssue count by type:")
        for t in by_type:
            lines.append(f"  • {t.get('issue_type', '—')}: {t.get('count', 0)}")

    lines.append("\n--- Schemes ---")
    for label, key_name in [
        ("Workflow Scheme", "workflow_scheme"),
        ("Permission Scheme", "permission_scheme"),
        ("Notification Scheme", "notification_scheme"),
    ]:
        val = snapshot.get(key_name)
        if val is not None:
            lines.append(f"\n{label}: {val}")

    wf_mapping = snapshot.get("workflow_scheme_mapping") or []
    if wf_mapping:
        lines.append("\n--- Workflow scheme mapping (issue type → workflow) ---")
        for m in wf_mapping:
            lines.append(f"  • {m.get('issue_type', '—')} → {m.get('workflow_name', '—')}")

    wf_details = snapshot.get("workflow_scheme_details")
    if wf_details:
        lines.append("\n--- Workflow scheme details (for reference / copy-paste; full XML in JSON) ---")
        lines.append(f"Scheme: {wf_details.get('scheme_name', '—')}")
        for wf in wf_details.get("workflows") or []:
            lines.append(f"\n  Workflow: {wf.get('workflow_name', '—')} | Issue types: {', '.join(wf.get('issue_types') or [])}")
            steps = wf.get("steps") or []
            if steps:
                lines.append("  Steps:")
                for s in steps:
                    lines.append(f"    • {s.get('id')}: {s.get('name', '—')}")
            trans = wf.get("transitions") or []
            if trans:
                lines.append("  Transitions:")
                for t in trans:
                    fr, to, name = t.get("from_step"), t.get("to_step"), t.get("name", "—")
                    line = f"    • {name} (step {fr} → {to})"
                    if t.get("conditions"):
                        line += f" [conditions: {len(t['conditions'])}]"
                    if t.get("validators"):
                        line += f" [validators: {len(t['validators'])}]"
                    if t.get("post_functions"):
                        line += f" [post-functions: {len(t['post_functions'])}]"
                    lines.append(line)
            if wf.get("parse_error"):
                lines.append("  (XML parse error; raw descriptor in JSON)")

    rules = snapshot.get("automation_rules") or []
    lines.append(f"\nAutomation Rules ({len(rules)}):")
    for r in rules:
        if isinstance(r, dict) and "NAME" in r:
            state = r.get("STATE", "")
            scope = r.get("SCOPE", "—")
            owner_display = _format_user_display(
                r.get("RULE_OWNER"), r.get("rule_owner_display_name"), r.get("rule_owner_email")
            )
            actor_display = _format_user_display(
                r.get("RULE_ACTOR"), r.get("rule_actor_display_name"), r.get("rule_actor_email")
            )
            lines.append(f"  • {r['NAME']} ({state}) | Scope: {scope} | Owner: {owner_display} | Actor: {actor_display}")

    sr = snapshot.get("sr_behaviors") or []
    count = snapshot.get("sr_behaviors_count", len(sr))
    lines.append(f"\nScriptRunner Behaviors ({count}):")
    for b in sr:
        if isinstance(b, dict):
            n = b.get("NAME", "")
            d = b.get("DESCRIPTION", "")
            pc = b.get("PROJECT_MAPPING_COUNT")
            ic = b.get("ISSUETYPE_MAPPING_COUNT")
            fc = b.get("FIELD_MAPPING_COUNT")
            extra = []
            if pc is not None:
                extra.append(f"Projects: {pc}")
            if ic is not None:
                extra.append(f"Issue types: {ic}")
            if fc is not None:
                extra.append(f"Fields: {fc}")
            suffix = " | " + ", ".join(extra) if extra else ""
            lines.append(f"  • {n}" + (f" — {d}" if d else "") + suffix)

    perm = snapshot.get("permission_details") or []
    lines.append(f"\nPermission Details ({len(perm)}):")
    for p in perm:
        if isinstance(p, dict):
            k = p.get("permission_key", "")
            t = (p.get("perm_type") or "").strip().lower()
            v = p.get("perm_parameter", "")
            if t == "user":
                v_display = _format_user_display(
                    v, p.get("perm_parameter_display_name"), p.get("perm_parameter_email")
                )
            elif t == "projectrole":
                v_display = _format_projectrole_display(v, p.get("perm_parameter_role_name"))
            else:
                v_display = v
            lines.append(f"  • {k} ({t}: {v_display})")

    screens = snapshot.get("screens_and_fields") or []
    lines.append(f"\nScreens and Fields ({len(screens)} entries):")
    seen = set()
    for s in screens:
        if isinstance(s, dict):
            it = s.get("issue_type") or ""
            sc = s.get("screen_name") or ""
            tab = s.get("tab_name") or ""
            fid = s.get("field_id") or ""
            fname = s.get("field_name") or fid
            req = s.get("required") or "—"
            proj_scope = s.get("field_project_scope") or "—"
            it_scope = s.get("field_issue_type_scope") or "—"
            key = (it, sc, tab, fid)
            if key not in seen:
                seen.add(key)
                lines.append(f"  • {it} / {sc} / {tab} — {fname} ({fid}) [{req}] Projects: {proj_scope}, Issue types: {it_scope}")

    cf = snapshot.get("custom_field_options") or []
    cf_grouped = _group_custom_field_options(cf)
    lines.append(f"\nCustom Field Options ({len(cf)} options in {len(cf_grouped)} fields):")
    for g in cf_grouped:
        fid = g.get("field_id") or ""
        n = g.get("cfname", "")
        vals = g.get("values_str", "")
        prefix = f"  • {fid}" if fid else "  •"
        if n:
            prefix += f" ({n})"
        lines.append(f"{prefix}: {vals}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def _h(s):
    """Escape for HTML."""
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _group_custom_field_options(cf_list):
    """Group custom_field_options by (field_id, cfname); values as comma-separated string. Returns list of dicts with field_id, cfname, values_str, option_count."""
    if not cf_list:
        return []
    groups = {}
    for c in cf_list:
        if not isinstance(c, dict):
            continue
        fid = c.get("field_id") or ""
        cfname = (c.get("cfname") or "").strip() or ""
        key = (fid, cfname)
        if key not in groups:
            groups[key] = []
        v = c.get("customvalue")
        if v is not None:
            groups[key].append(str(v).strip())
    out = []
    for (fid, cfname), values in groups.items():
        out.append({
            "field_id": fid,
            "cfname": cfname,
            "values_str": ", ".join(values),
            "option_count": len(values),
        })
    return out


def build_audit_summary_html(snapshot, table_class="audit-table"):
    """
    Build an HTML summary with tables: object category and object names for admin readability.
    Full data (no truncation). Returns HTML string suitable for browser display.
    """
    key = _h(snapshot.get("project_key", ""))
    name = _h(snapshot.get("project_name", ""))
    parts = ['<div class="audit-summary">']
    parts.append(f'<header class="summary-header"><h2>JIRA PROJECT CONFIG SUMMARY</h2><p class="summary-project">{key} — {name}</p></header>')

    # Project metadata — all captured fields at top
    lead_display = _h(_format_user_display(
        snapshot.get("project_lead"),
        snapshot.get("project_lead_display_name"),
        snapshot.get("project_lead_email"),
    ))
    cat = _h(snapshot.get("project_category") or "—")
    assignee_type = _h(snapshot.get("default_assignee_type") or "—")
    its = _h(snapshot.get("issue_type_scheme") or "—")
    total = snapshot.get("total_issue_count")
    total_s = str(total) if total is not None else "—"
    comp = snapshot.get("component_count")
    comp_s = str(comp) if comp is not None else "—"
    ver = snapshot.get("version_count")
    ver_s = str(ver) if ver is not None else "—"
    perm_count = snapshot.get("permission_entry_count")
    perm_count_s = str(perm_count) if perm_count is not None else "—"
    last_key = _h(snapshot.get("last_issue_key") or "—")
    last_created = _h(snapshot.get("last_issue_created") or "—")
    last_up_key = _h(snapshot.get("last_updated_issue_key") or "—")
    last_up_ts = _h(snapshot.get("last_updated_issue_timestamp") or "—")
    parts.append(
        '<details class="summary-section summary-metadata"><summary><h3>Project metadata</h3></summary><div class="section-content">'
        f'<table class="{_h(table_class)}"><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>'
        f'<tr><td>Project Key</td><td><strong>{key}</strong></td></tr>'
        f'<tr><td>Project Name</td><td>{name}</td></tr>'
        f'<tr><td>Project Lead</td><td>{lead_display}</td></tr>'
        f'<tr><td>Project Category</td><td>{cat}</td></tr>'
        f'<tr><td>Default Assignee Type</td><td>{assignee_type}</td></tr>'
        f'<tr><td>Issue Type Scheme</td><td>{its}</td></tr>'
    )
    it_list = snapshot.get("issue_type_scheme_issue_types") or []
    if it_list:
        it_list_str = _h(", ".join(it_list))
        parts.append(f'<tr><td>Issue types in scheme ({len(it_list)})</td><td>{it_list_str}</td></tr>')
    parts.append(
        f'<tr><td>Total Issue Count</td><td>{total_s}</td></tr>'
        f'<tr><td>Component Count</td><td>{comp_s}</td></tr>'
        f'<tr><td>Version Count</td><td>{ver_s}</td></tr>'
        f'<tr><td>Permission Entries</td><td>{perm_count_s}</td></tr>'
        f'<tr><td>Last Created Issue</td><td><code>{last_key}</code></td></tr>'
        f'<tr><td>Last Issue Created (timestamp)</td><td>{last_created}</td></tr>'
        f'<tr><td>Last Updated Issue</td><td><code>{last_up_key}</code></td></tr>'
        f'<tr><td>Last Updated (timestamp)</td><td>{last_up_ts}</td></tr>'
        '</tbody></table></div></details>'
    )
    # Issue count by type (sub-table under metadata)
    by_type = snapshot.get("issue_count_by_type") or []
    if by_type:
        parts.append(
            '<details class="summary-section summary-metadata-counts"><summary><h3>Issue count by type</h3></summary><div class="section-content">'
            f'<table class="{_h(table_class)}"><thead><tr><th>Issue Type</th><th>Count</th></tr></thead><tbody>'
        )
        for t in by_type:
            parts.append(f"<tr><td>{_h(t.get('issue_type', '—'))}</td><td>{int(t.get('count', 0))}</td></tr>")
        parts.append("</tbody></table></div></details>")

    # Schemes
    parts.append('<details class="summary-section summary-schemes"><summary><h3>Schemes</h3></summary><div class="section-content"><table class="%s"><thead><tr><th>Category</th><th>Name</th></tr></thead><tbody>' % _h(table_class))
    for label, key_name in [
        ("Workflow Scheme", "workflow_scheme"),
        ("Permission Scheme", "permission_scheme"),
        ("Notification Scheme", "notification_scheme"),
    ]:
        val = snapshot.get(key_name)
        if val is not None:
            parts.append(f"<tr><td>{_h(label)}</td><td>{_h(val)}</td></tr>")
    parts.append("</tbody></table></div></details>")

    # Workflow scheme mapping (issue type → workflow) for quick comparison
    wf_mapping = snapshot.get("workflow_scheme_mapping") or []
    if wf_mapping:
        parts.append(
            f'<details class="summary-section summary-workflow-mapping"><summary><h3>Workflow scheme mapping (issue type → workflow)</h3></summary><div class="section-content">'
            f'<table class="{table_class}"><thead><tr><th>Issue Type</th><th>Workflow</th></tr></thead><tbody>'
        )
        for m in wf_mapping:
            parts.append(f"<tr><td>{_h(m.get('issue_type', '—'))}</td><td>{_h(m.get('workflow_name', '—'))}</td></tr>")
        parts.append("</tbody></table></div></details>")

    # Versions (releases) list
    versions = snapshot.get("versions") or []
    if versions:
        parts.append(
            f'<details class="summary-section summary-versions"><summary><h3>Versions ({len(versions)})</h3></summary><div class="section-content">'
            f'<table class="{table_class}"><thead><tr><th>Name</th><th>Released</th><th>Archived</th></tr></thead><tbody>'
        )
        for v in versions:
            rel = _h("Yes" if v.get("released") else "No")
            arch = _h("Yes" if v.get("archived") else "No")
            parts.append(f"<tr><td>{_h(v.get('name') or '—')}</td><td>{rel}</td><td>{arch}</td></tr>")
        parts.append("</tbody></table></div></details>")

    # Components list
    components = snapshot.get("components") or []
    if components:
        parts.append(
            f'<details class="summary-section summary-components"><summary><h3>Components ({len(components)})</h3></summary><div class="section-content">'
            f'<table class="{table_class}"><thead><tr><th>Name</th><th>Lead</th><th>Description</th></tr></thead><tbody>'
        )
        for c in components:
            parts.append(f"<tr><td>{_h(c.get('name') or '—')}</td><td>{_h(c.get('lead') or '—')}</td><td>{_h((c.get('description') or '')[:200])}</td></tr>")
        parts.append("</tbody></table></div></details>")

    # Workflow scheme details (steps, transitions, conditions/validators; full XML in JSON for copy-paste)
    wf_details = snapshot.get("workflow_scheme_details")
    if wf_details:
        parts.append(
            f'<details class="summary-section summary-workflow-details"><summary><h3>Workflow scheme details</h3></summary><div class="section-content">'
            f'<p class="workflow-details-intro">Scheme: <strong>{_h(wf_details.get("scheme_name", ""))}</strong>. '
            'Steps, transitions, conditions, validators, and post-functions below; full descriptor XML is in the JSON export for copy-paste.</p>'
        )
        for wf in wf_details.get("workflows") or []:
            wf_name = _h(wf.get("workflow_name", ""))
            it_list = ", ".join(_h(x) for x in (wf.get("issue_types") or []))
            parts.append(f'<div class="workflow-block"><h4>{wf_name} <span class="workflow-issue-types">({it_list})</span></h4>')
            steps = wf.get("steps") or []
            if steps:
                parts.append('<div class="workflow-steps-table-wrapper">')
                parts.append(
                    f'<table class="{table_class} workflow-steps-table"><thead><tr><th>Step ID</th><th>Step name</th></tr></thead><tbody>'
                )
                for s in steps:
                    parts.append(f"<tr><td>{_h(s.get('id'))}</td><td>{_h(s.get('name', '—'))}</td></tr>")
                parts.append("</tbody></table></div>")
            trans = wf.get("transitions") or []
            if trans:
                parts.append('<div class="workflow-transitions-table-wrapper">')
                parts.append(
                    f'<table class="{table_class} workflow-transitions-table"><thead><tr><th>Transition</th><th>From step</th><th>To step</th><th>Conditions</th><th>Validators</th><th>Post-functions</th></tr></thead><tbody>'
                )
                for t in trans:
                    conds = t.get("conditions") or []
                    vals = t.get("validators") or []
                    posts = t.get("post_functions") or []
                    cond_str = "; ".join((c.get("class") or c.get("type") or "—") for c in conds[:5])
                    if len(conds) > 5:
                        cond_str += f" (+{len(conds)-5})"
                    val_str = "; ".join((v.get("class") or v.get("type") or "—") for v in vals[:5])
                    if len(vals) > 5:
                        val_str += f" (+{len(vals)-5})"
                    post_str = "; ".join((p.get("class") or p.get("type") or "—") for p in posts[:5])
                    if len(posts) > 5:
                        post_str += f" (+{len(posts)-5})"
                    parts.append(
                        f"<tr><td>{_h(t.get('name'))}</td><td>{_h(t.get('from_step'))}</td><td>{_h(t.get('to_step'))}</td>"
                        f"<td>{_h(cond_str or '—')}</td><td>{_h(val_str or '—')}</td><td>{_h(post_str or '—')}</td></tr>"
                    )
                parts.append("</tbody></table></div>")
            if wf.get("descriptor_xml"):
                parts.append(
                    '<details class="workflow-xml-details"><summary>Descriptor XML (copy-paste)</summary>'
                    f'<pre class="workflow-xml-pre">{_h(wf.get("descriptor_xml")[:50000])}</pre></details>'
                )
            if wf.get("parse_error"):
                parts.append('<p class="workflow-parse-warn">(XML parse error; raw descriptor available in JSON export.)</p>')
            parts.append("</div>")
        parts.append("</div></details>")

    # Automation Rules (full list): name, state, scope, rule owner, rule actor
    rules = snapshot.get("automation_rules") or []
    parts.append(
        f'<details class="summary-section summary-automation"><summary><h3>Automation Rules ({len(rules)})</h3></summary><div class="section-content">'
        f'<table class="{table_class}"><thead><tr><th>Rule Name</th><th>State</th><th>Scope</th><th>Rule Owner</th><th>Rule Actor</th></tr></thead><tbody>'
    )
    for r in rules:
        if isinstance(r, dict):
            state = (r.get("STATE") or "").strip().upper()
            state_cls = "state-enabled" if state == "ENABLED" else "state-disabled"
            scope = _h(r.get("SCOPE") or "—")
            owner_display = _h(_format_user_display(
                r.get("RULE_OWNER"), r.get("rule_owner_display_name"), r.get("rule_owner_email")
            ))
            actor_display = _h(_format_user_display(
                r.get("RULE_ACTOR"), r.get("rule_actor_display_name"), r.get("rule_actor_email")
            ))
            parts.append(
                f"<tr><td>{_h(r.get('NAME'))}</td><td class=\"{state_cls}\">{_h(r.get('STATE'))}</td>"
                f"<td>{scope}</td><td>{owner_display}</td><td>{actor_display}</td></tr>"
            )
    parts.append("</tbody></table></div></details>")

    # ScriptRunner Behaviors (with project/issuetype/field mapping counts when available)
    sr = snapshot.get("sr_behaviors") or []
    count = snapshot.get("sr_behaviors_count", len(sr))
    parts.append(
        f'<details class="summary-section summary-behaviors"><summary><h3>ScriptRunner Behaviors ({count})</h3></summary><div class="section-content">'
        f'<table class="{table_class}"><thead><tr><th>Behavior Name</th><th>Description</th><th>Project mappings</th><th>Issue type mappings</th><th>Field mappings</th></tr></thead><tbody>'
    )
    for b in sr:
        if isinstance(b, dict):
            pc = b.get("PROJECT_MAPPING_COUNT")
            ic = b.get("ISSUETYPE_MAPPING_COUNT")
            fc = b.get("FIELD_MAPPING_COUNT")
            pc_s = str(pc) if pc is not None else "—"
            ic_s = str(ic) if ic is not None else "—"
            fc_s = str(fc) if fc is not None else "—"
            parts.append(
                f"<tr><td>{_h(b.get('NAME'))}</td><td>{_h(b.get('DESCRIPTION'))}</td>"
                f"<td>{pc_s}</td><td>{ic_s}</td><td>{fc_s}</td></tr>"
            )
    parts.append("</tbody></table></div></details>")

    # Permission Details (full list)
    perm = snapshot.get("permission_details") or []
    parts.append(f'<details class="summary-section summary-permissions"><summary><h3>Permission Details ({len(perm)})</h3></summary><div class="section-content"><table class="{table_class}"><thead><tr><th>Permission Key</th><th>Type</th><th>Parameter</th></tr></thead><tbody>')
    for p in perm:
        if isinstance(p, dict):
            t = (p.get("perm_type") or "").strip().lower()
            v = p.get("perm_parameter")
            if t == "user":
                v_display = _format_user_display(
                    v, p.get("perm_parameter_display_name"), p.get("perm_parameter_email")
                )
            elif t == "projectrole":
                v_display = _format_projectrole_display(v, p.get("perm_parameter_role_name"))
            else:
                v_display = v
            parts.append(f"<tr><td>{_h(p.get('permission_key'))}</td><td>{_h(p.get('perm_type'))}</td><td>{_h(v_display)}</td></tr>")
    parts.append("</tbody></table></div></details>")

    # Screens and Fields — full list (no truncation)
    screens = snapshot.get("screens_and_fields") or []
    parts.append(f'<details class="summary-section summary-screens-fields"><summary><h3>Screens and Fields ({len(screens)})</h3></summary><div class="section-content"><table class="{table_class} screens-fields-table"><thead><tr><th>Issue Type</th><th>Screen</th><th>Tab</th><th>Field ID</th><th>Field Name</th><th>Required/Optional</th><th>Projects</th><th>Issue types</th></tr></thead><tbody>')
    seen = set()
    for s in screens:
        if isinstance(s, dict):
            it = s.get("issue_type") or ""
            sc = s.get("screen_name") or ""
            tab = s.get("tab_name") or ""
            fid = s.get("field_id") or ""
            fname = s.get("field_name") or fid
            req = (s.get("required") or "—").strip()
            proj_scope = _h(s.get("field_project_scope") or "—")
            it_scope = _h(s.get("field_issue_type_scope") or "—")
            key_tuple = (it, sc, tab, fid)
            if key_tuple not in seen:
                seen.add(key_tuple)
                req_cls = "req-required" if req.lower() == "required" else "req-optional"
                parts.append(f"<tr><td>{_h(it)}</td><td>{_h(sc)}</td><td>{_h(tab)}</td><td><code>{_h(fid)}</code></td><td>{_h(fname)}</td><td class=\"{req_cls}\">{_h(req)}</td><td>{proj_scope}</td><td>{it_scope}</td></tr>")
    parts.append("</tbody></table></div></details>")

    # Custom Field Options (grouped by field: one row per field, values comma-separated)
    cf = snapshot.get("custom_field_options") or []
    cf_grouped = _group_custom_field_options(cf)
    total_opts = len(cf)
    parts.append(f'<details class="summary-section summary-custom-fields"><summary><h3>Custom Field Options ({total_opts} options in {len(cf_grouped)} fields)</h3></summary><div class="section-content">')
    parts.append(f'<table class="{table_class} summary-custom-fields-table"><thead><tr><th>Field ID</th><th>Field Name</th><th>Values</th></tr></thead><tbody>')
    for g in cf_grouped:
        fid = _h(g.get("field_id") or "—")
        cfname = _h(g.get("cfname") or "—")
        vals = _h(g.get("values_str") or "—")
        parts.append(f"<tr><td><code>{fid}</code></td><td>{cfname}</td><td class=\"cf-values-cell\">{vals}</td></tr>")
    parts.append("</tbody></table></div></details>")

    parts.append("</div>")
    return "\n".join(parts)


def get_db_connection(config, instance):
    s = config[instance]
    return mysql.connector.connect(
        host=s['host'], user=s['user'], password=s['password'], 
        database=s['database'], port=s.getint('port', 3306)
    )


def fetch_user_display_batch(cursor, user_identifiers):
    """
    Resolve user_key / lower_user_name to display_name and email via app_user + cwd_user.
    user_identifiers: list of strings (user_key or lower_user_name from Jira).
    Returns dict: identifier -> {"display_name": str or None, "email": str or None}.
    """
    out = {}
    ids = [x for x in user_identifiers if x and str(x).strip()]
    if not ids:
        return out
    ids = list(dict.fromkeys(ids))
    try:
        # Jira: app_user links to cwd_user via lower_user_name; cwd_user has display_name, email_address
        placeholders = ", ".join(["%s"] * len(ids))
        query = (
            "SELECT a.`user_key`, a.`lower_user_name`, c.`display_name`, c.`email_address` "
            "FROM `app_user` a "
            "LEFT JOIN `cwd_user` c ON a.`lower_user_name` = c.`lower_user_name` "
            f"WHERE a.`user_key` IN ({placeholders}) OR a.`lower_user_name` IN ({placeholders})"
        )
        cursor.execute(query, ids + ids)
        for row in cursor.fetchall():
            dn = (row.get("display_name") or "").strip() or None
            em = (row.get("email_address") or "").strip() or None
            info = {"display_name": dn, "email": em}
            uk = row.get("user_key")
            ln = row.get("lower_user_name")
            if uk:
                out[uk] = info
            if ln:
                out[ln] = info
        return out
    except Exception:
        # cwd_user or columns may not exist in some Jira setups
        return out


def fetch_project_role_names_batch(cursor, role_ids):
    """
    Resolve project role IDs to role names via projectrole table.
    role_ids: list of role IDs (int or str from schemepermissions.perm_parameter when perm_type='projectrole').
    Returns dict: role_id (normalized to str) -> role_name (str or None).
    """
    out = {}
    ids = []
    for x in role_ids:
        if x is None:
            continue
        try:
            xi = int(x)
            ids.append(xi)
        except (TypeError, ValueError):
            pass
    if not ids:
        return out
    ids = list(dict.fromkeys(ids))
    try:
        placeholders = ", ".join(["%s"] * len(ids))
        query = "SELECT `id`, `name` FROM `projectrole` WHERE `id` IN (" + placeholders + ")"
        cursor.execute(query, ids)
        for row in cursor.fetchall():
            rid = row.get("id")
            name = (row.get("name") or "").strip() or None
            if rid is not None:
                out[str(rid)] = name
        return out
    except Exception:
        # projectrole table/columns may not exist in some Jira setups
        return out


def enrich_snapshot_with_user_info(cursor, snapshot):
    """
    Cross-reference user table and projectrole table to add display names wherever ids appear.
    Mutates snapshot: adds project_lead_display_name, project_lead_email; for each
    automation rule rule_owner_display_name, rule_owner_email, rule_actor_display_name,
    rule_actor_email; for each permission entry (when user) perm_parameter_display_name,
    perm_parameter_email; for each permission entry (when projectrole) perm_parameter_role_name.
    Keeps existing id fields unchanged. JSON and UI show id / name for users and project roles.
    """
    identifiers = []
    lead = snapshot.get("project_lead")
    if lead:
        identifiers.append(lead)
    for r in snapshot.get("automation_rules") or []:
        if isinstance(r, dict):
            o = r.get("RULE_OWNER")
            a = r.get("RULE_ACTOR")
            if o:
                identifiers.append(o)
            if a:
                identifiers.append(a)
    role_ids = []
    for p in snapshot.get("permission_details") or []:
        if isinstance(p, dict):
            if (p.get("perm_type") or "").strip().lower() == "user":
                v = p.get("perm_parameter")
                if v:
                    identifiers.append(v)
            elif (p.get("perm_type") or "").strip().lower() == "projectrole":
                v = p.get("perm_parameter")
                if v is not None:
                    role_ids.append(v)
    cache = fetch_user_display_batch(cursor, identifiers)
    role_name_cache = fetch_project_role_names_batch(cursor, role_ids)

    def get_info(key):
        return cache.get(key) or {"display_name": None, "email": None}

    info = get_info(lead) if lead else {"display_name": None, "email": None}
    snapshot["project_lead_display_name"] = info["display_name"]
    snapshot["project_lead_email"] = info["email"]

    for r in snapshot.get("automation_rules") or []:
        if not isinstance(r, dict):
            continue
        o = r.get("RULE_OWNER")
        a = r.get("RULE_ACTOR")
        ro = get_info(o) if o else {"display_name": None, "email": None}
        ra = get_info(a) if a else {"display_name": None, "email": None}
        r["rule_owner_display_name"] = ro["display_name"]
        r["rule_owner_email"] = ro["email"]
        r["rule_actor_display_name"] = ra["display_name"]
        r["rule_actor_email"] = ra["email"]

    for p in snapshot.get("permission_details") or []:
        if not isinstance(p, dict):
            continue
        if (p.get("perm_type") or "").strip().lower() == "user":
            v = p.get("perm_parameter")
            info = get_info(v) if v else {"display_name": None, "email": None}
            p["perm_parameter_display_name"] = info["display_name"]
            p["perm_parameter_email"] = info["email"]
        elif (p.get("perm_type") or "").strip().lower() == "projectrole":
            v = p.get("perm_parameter")
            p["perm_parameter_role_name"] = role_name_cache.get(str(v)) if v is not None else None


## --- DATA GATHERING MODULES --- ##

def fetch_project_pulse(cursor, project_key):
    """Retrieves basic project metadata. Uses backticks for MySQL 8 safety."""
    query = "SELECT `ID`, `pname`, `lead` FROM `project` WHERE `pkey` = %s"
    cursor.execute(query, (project_key,))
    return cursor.fetchone()

def fetch_last_created_issue(cursor, project_id, project_key):
    """Returns the most recently created issue in the project: issue_key, created timestamp."""
    try:
        query = (
            "SELECT CONCAT(%s, '-', j.`issuenum`) AS issue_key, j.`CREATED` AS created "
            "FROM `jiraissue` j WHERE j.`PROJECT` = %s ORDER BY j.`CREATED` DESC LIMIT 1"
        )
        cursor.execute(query, (project_key, project_id))
        row = cursor.fetchone()
        if not row:
            return None
        created = row.get("created")
        if hasattr(created, "isoformat"):
            created = created.isoformat()
        return {"last_issue_key": row.get("issue_key"), "last_issue_created": created}
    except Exception:
        return None

def fetch_total_issue_count(cursor, project_id):
    """Total number of issues in the project."""
    try:
        cursor.execute("SELECT COUNT(*) AS cnt FROM `jiraissue` WHERE `PROJECT` = %s", (project_id,))
        row = cursor.fetchone()
        return int(row["cnt"]) if row else 0
    except Exception:
        return None

def fetch_last_updated_issue(cursor, project_id, project_key):
    """Most recently updated issue in the project: issue_key, updated timestamp."""
    try:
        query = (
            "SELECT CONCAT(%s, '-', j.`issuenum`) AS issue_key, j.`UPDATED` AS updated "
            "FROM `jiraissue` j WHERE j.`PROJECT` = %s ORDER BY j.`UPDATED` DESC LIMIT 1"
        )
        cursor.execute(query, (project_key, project_id))
        row = cursor.fetchone()
        if not row:
            return None
        updated = row.get("updated")
        if hasattr(updated, "isoformat"):
            updated = updated.isoformat()
        return {"last_updated_issue_key": row.get("issue_key"), "last_updated_issue_timestamp": updated}
    except Exception:
        return None

def fetch_issue_count_by_type(cursor, project_id, project_key):
    """Issue counts grouped by issue type. Returns list of dicts: issue_type, count."""
    try:
        query = (
            "SELECT it.`pname` AS issue_type, COUNT(j.`id`) AS cnt FROM `jiraissue` j "
            "LEFT JOIN `issuetype` it ON j.`issuetype` = it.`id` "
            "WHERE j.`PROJECT` = %s GROUP BY j.`issuetype` ORDER BY cnt DESC"
        )
        cursor.execute(query, (project_id,))
        rows = cursor.fetchall()
        return [{"issue_type": (r.get("issue_type") or "—"), "count": int(r.get("cnt", 0))} for r in rows]
    except Exception:
        return []

def fetch_component_count(cursor, project_id):
    """Number of components in the project."""
    try:
        cursor.execute("SELECT COUNT(*) AS cnt FROM `component` WHERE `PROJECT` = %s", (project_id,))
        row = cursor.fetchone()
        return int(row["cnt"]) if row else 0
    except Exception:
        return None

def fetch_version_count(cursor, project_id):
    """Number of versions (affects / fix for) in the project."""
    try:
        cursor.execute("SELECT COUNT(*) AS cnt FROM `projectversion` WHERE `PROJECT` = %s", (project_id,))
        row = cursor.fetchone()
        return int(row["cnt"]) if row else 0
    except Exception:
        return None


def fetch_versions(cursor, project_id):
    """List of versions/releases for the project: id, name, released, archived (for audit/comparison)."""
    try:
        cursor.execute(
            "SELECT `id`, `name`, `released`, `archived` FROM `projectversion` WHERE `PROJECT` = %s ORDER BY `name`",
            (project_id,),
        )
        rows = cursor.fetchall()
        out = []
        for r in rows:
            out.append({
                "id": r.get("id"),
                "name": (r.get("name") or "").strip() or None,
                "released": r.get("released"),
                "archived": r.get("archived"),
            })
        return out
    except Exception:
        return []


def fetch_components(cursor, project_id):
    """List of components for the project: id, name, lead, description (for audit/comparison)."""
    try:
        cursor.execute(
            "SELECT `id`, `name`, `lead`, `description` FROM `component` WHERE `PROJECT` = %s ORDER BY `name`",
            (project_id,),
        )
        rows = cursor.fetchall()
        out = []
        for r in rows:
            out.append({
                "id": r.get("id"),
                "name": (r.get("name") or "").strip() or None,
                "lead": (r.get("lead") or "").strip() or None,
                "description": (r.get("description") or "").strip() or None,
            })
        return out
    except Exception:
        return []


def fetch_issue_type_scheme_issue_types(cursor, project_key):
    """List of all issue type names in the project's issue type (screen) scheme, including those with 0 issues."""
    for (na_entity, table, entity_table) in [
        ("IssueTypeScreenScheme", "issuetypescreenscheme", "issuetypescreenschemeentity"),
        ("IssueTypeScheme", "issuetypescheme", "issuetypeschemeentity"),
    ]:
        try:
            # Get scheme id for this project
            cursor.execute(
                f"SELECT s.`id` AS scheme_id FROM `project` p "
                f"JOIN `nodeassociation` na ON p.`id` = na.`source_node_id` AND na.`sink_node_entity` = %s "
                f"JOIN `{table}` s ON na.`sink_node_id` = s.`id` WHERE p.`pkey` = %s",
                (na_entity, project_key),
            )
            row = cursor.fetchone()
            if not row or not row.get("scheme_id"):
                continue
            scheme_id = row["scheme_id"]
            # Discover entity table column names (issuetype vs issue_type etc.)
            it_col = _get_actual_column(cursor, entity_table, "issuetype", "issue_type")
            scheme_col = _get_actual_column(cursor, entity_table, "scheme")
            if not scheme_col:
                continue
            # Distinct issue type ids in this scheme
            cursor.execute(
                f"SELECT DISTINCT `{it_col}` AS it_id FROM `{entity_table}` WHERE `{scheme_col}` = %s",
                (scheme_id,),
            )
            it_ids = [r["it_id"] for r in cursor.fetchall() if r.get("it_id") is not None]
            if not it_ids:
                continue
            # Resolve to names
            placeholders = ", ".join(["%s"] * len(it_ids))
            cursor.execute(f"SELECT `id`, `pname` FROM `issuetype` WHERE `id` IN ({placeholders})", it_ids)
            names = {str(r["id"]): (r.get("pname") or "").strip() for r in cursor.fetchall()}
            return [names.get(str(i), str(i)) or str(i) for i in it_ids]
        except Exception:
            continue
    return []


def fetch_issue_type_scheme_name(cursor, project_key):
    """Name of the issue type (screen) scheme attached to the project, if any."""
    # Project is linked to IssueTypeScreenScheme in Jira DC
    for (na_entity, table) in [("IssueTypeScreenScheme", "issuetypescreenscheme"), ("IssueTypeScheme", "issuetypescheme")]:
        try:
            query = (
                f"SELECT s.`name` AS scheme_name FROM `project` p "
                f"JOIN `nodeassociation` na ON p.`id` = na.`source_node_id` AND na.`sink_node_entity` = %s "
                f"JOIN `{table}` s ON na.`sink_node_id` = s.`id` "
                "WHERE p.`pkey` = %s"
            )
            cursor.execute(query, (na_entity, project_key))
            row = cursor.fetchone()
            if row and row.get("scheme_name"):
                return row["scheme_name"]
        except Exception:
            continue
    return None

def fetch_project_category(cursor, project_key):
    """Project category name if project has a category."""
    try:
        query = (
            "SELECT pc.`name` AS category_name FROM `project` p "
            "LEFT JOIN `projectcategory` pc ON p.`category` = pc.`id` WHERE p.`pkey` = %s"
        )
        cursor.execute(query, (project_key,))
        row = cursor.fetchone()
        return (row.get("category_name") or "").strip() or None
    except Exception:
        return None

def fetch_default_assignee_type(cursor, project_key):
    """Default assignee type for the project (e.g. UNASSIGNED, PROJECT_LEAD)."""
    try:
        cursor.execute("SELECT `assignee_type` FROM `project` WHERE `pkey` = %s", (project_key,))
        row = cursor.fetchone()
        return (row.get("assignee_type") or "").strip() or None
    except Exception:
        return None

def fetch_blueprint(cursor, project_key):
    """Captures core schemes (Workflow, Permission, Notification) and workflow scheme id for detail lookup."""
    query = (
        "SELECT ws.`id` AS workflow_scheme_id, ws.`name` AS workflow_scheme, "
        "ps.`name` AS permission_scheme, ns.`name` AS notification_scheme "
        "FROM `project` p "
        "LEFT JOIN `nodeassociation` na2 ON p.`id` = na2.`source_node_id` AND na2.`sink_node_entity` = 'WorkflowScheme' "
        "LEFT JOIN `workflowscheme` ws ON na2.`sink_node_id` = ws.`id` "
        "LEFT JOIN `nodeassociation` na3 ON p.`id` = na3.`source_node_id` AND na3.`sink_node_entity` = 'PermissionScheme' "
        "LEFT JOIN `permissionscheme` ps ON na3.`sink_node_id` = ps.`id` "
        "LEFT JOIN `nodeassociation` na4 ON p.`id` = na4.`source_node_id` AND na4.`sink_node_entity` = 'NotificationScheme' "
        "LEFT JOIN `notificationscheme` ns ON na4.`sink_node_id` = ns.`id` "
        "WHERE p.`pkey` = %s"
    )
    cursor.execute(query, (project_key,))
    return cursor.fetchone()


def _extract_arg_dict(parent_el):
    """Extract all <arg name="...">value</arg> from an element into a dict. Jira uses arg name='class.name' for class."""
    if parent_el is None:
        return {}
    out = {}
    for arg in parent_el.findall("arg"):
        name = arg.get("name")
        if name:
            val = (arg.text or "").strip() or arg.get("value") or ""
            out[name] = val
    return out


def _parse_workflow_descriptor_xml(xml_str):
    """
    Parse Jira workflow descriptor XML (OSWorkflow format). Returns dict with steps, transitions,
    and per-transition conditions/validators/post-functions where parseable. Includes raw_xml for copy-paste.
    Jira stores class names in <arg name="class.name">...; conditions under restrict-to/conditions; post-functions under results/unconditional-result/post-functions.
    """
    if not xml_str or not xml_str.strip():
        return None
    try:
        root = ET.fromstring(xml_str.strip())
    except ET.ParseError:
        return {"parse_error": True}
    out = {"steps": [], "transitions": []}
    # Steps: <steps><step id="1" name="Open"/></steps> or <step id="1"><name>Open</name></step>
    steps_el = root.find("steps")
    if steps_el is not None:
        for step in steps_el.findall("step"):
            sid = step.get("id")
            name = step.get("name") or (step.find("name") is not None and (step.find("name").text or "").strip())
            if sid is not None:
                out["steps"].append({"id": sid, "name": name or sid})
    # Actions (transitions): common-actions has <action> children directly; steps have <actions><action>
    def collect_actions(actions_el, from_step=None):
        if actions_el is None:
            return
        for action in actions_el.findall("action"):
            aid = action.get("id")
            aname = action.get("name") or (action.find("name") is not None and (action.find("name").text or "").strip()) or aid
            to_step = None
            results = action.find("results")
            unc = results.find("unconditional-result") if results is not None else None
            if unc is not None:
                to_step = unc.get("step")
            tr = {"action_id": aid, "name": aname, "from_step": from_step, "to_step": to_step, "conditions": [], "validators": [], "post_functions": []}
            # Conditions: <restrict-to><conditions><condition type="class"><arg name="class.name">...</arg></condition></restrict-to>
            restrict = action.find("restrict-to")
            if restrict is not None:
                conds = restrict.find("conditions")
                if conds is not None:
                    for c in conds.findall("condition"):
                        ctype = c.get("type") or ""
                        args = _extract_arg_dict(c)
                        cclass = args.get("class.name") or c.get("class")
                        tr["conditions"].append({"type": ctype, "class": cclass, "args": args})
            # Validators: <validators><validator type="class"><arg name="class.name">...</arg></validator></validators>
            validators = action.find("validators")
            if validators is not None:
                for v in validators.findall("validator"):
                    vtype = v.get("type") or ""
                    vargs = _extract_arg_dict(v)
                    vclass = vargs.get("class.name") or v.get("class")
                    tr["validators"].append({"type": vtype, "class": vclass, "args": vargs})
            # Post-functions: under results/unconditional-result/post-functions (Jira uses <function>, not <post-function>)
            postf = (unc.find("post-functions") if unc is not None else None) or action.find("post-functions")
            if postf is not None:
                for pf in postf.findall("function") or postf.findall("post-function"):
                    ptype = pf.get("type") or ""
                    args = _extract_arg_dict(pf)
                    pclass = args.get("class.name") or pf.get("class")
                    tr["post_functions"].append({"type": ptype, "class": pclass, "args": args})
            out["transitions"].append(tr)
    # Global actions (meta/actions)
    meta_global = root.find(".//meta[@name='global']") or root.find("meta")
    if meta_global is not None:
        actions_el = meta_global.find("actions")
        collect_actions(actions_el)
    # initial-actions: e.g. Create (children are <action> directly)
    for initial in root.findall("initial-actions"):
        collect_actions(initial, from_step=None)
    # common-actions: children are <action> directly (no wrapper <actions>)
    for common in root.findall("common-actions"):
        collect_actions(common, from_step=None)
    # Per-step actions: <step id="1"><actions><action>...</action></actions></step>
    if steps_el is not None:
        for step in steps_el.findall("step"):
            from_sid = step.get("id")
            actions_el = step.find("actions")
            collect_actions(actions_el, from_step=from_sid)
    return out


def fetch_workflow_scheme_details(cursor, project_key, workflow_scheme_id=None, workflow_scheme_name=None):
    """
    Fetch workflow scheme details for the project: which workflows (by name) map to which issue types,
    and for each workflow the descriptor XML (steps, transitions, conditions, validators, post-functions).
    workflow_scheme_id and workflow_scheme_name can be passed from the audit snapshot to avoid re-querying.
    Returns None if tables/columns are missing or on error; otherwise dict with scheme_name, scheme_id, workflows list.
    """
    try:
        if workflow_scheme_id is None or not (workflow_scheme_name or "").strip():
            blueprint = fetch_blueprint(cursor, project_key)
            if not blueprint:
                return None
            workflow_scheme_id = blueprint.get("workflow_scheme_id")
            workflow_scheme_name = (blueprint.get("workflow_scheme") or "").strip()
        scheme_id = workflow_scheme_id
        scheme_name = (workflow_scheme_name or "").strip()
        if not scheme_id or not scheme_name:
            return None
        # Discover workflowschemeentity table (may be workflowschemeentity or similar)
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND LOWER(TABLE_NAME) = 'workflowschemeentity'
        """)
        if not cursor.fetchone():
            return None
        t_entity = "workflowschemeentity"
        scheme_col = _get_actual_column(cursor, t_entity, "scheme")
        workflow_col = _get_actual_column(cursor, t_entity, "workflow", "workflowname")
        it_col = _get_actual_column(cursor, t_entity, "issuetype", "issue_type")
        if not scheme_col or not workflow_col:
            return None
        # Get (issuetype, workflow name) for this scheme
        cursor.execute(
            f"SELECT `{scheme_col}`, `{workflow_col}`" + (f", `{it_col}`" if it_col else "") + f" FROM `{t_entity}` WHERE `{scheme_col}` = %s",
            (scheme_id,),
        )
        entities = cursor.fetchall()
        if not entities:
            return None
        # Build list of distinct workflow names and issue type mapping
        workflow_to_issue_types = {}
        for row in entities:
            wf_name = (row.get(workflow_col) or row.get("workflow") or row.get("workflowname") or "").strip()
            if not wf_name:
                continue
            it_val = row.get(it_col or "issuetype") if it_col else None
            if wf_name not in workflow_to_issue_types:
                workflow_to_issue_types[wf_name] = []
            if it_val is not None:
                workflow_to_issue_types[wf_name].append(it_val)
            else:
                workflow_to_issue_types[wf_name].append("(default)")
        # Discover jiraworkflows table
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND LOWER(TABLE_NAME) = 'jiraworkflows'
        """)
        if not cursor.fetchone():
            return None
        wf_name_col = _get_actual_column(cursor, "jiraworkflows", "workflowname", "workflow_name", "name")
        desc_col = _get_actual_column(cursor, "jiraworkflows", "descriptor")
        if not wf_name_col or not desc_col:
            return None
        result = {"scheme_name": scheme_name, "scheme_id": scheme_id, "workflows": []}
        # Resolve issue type ids to names for display
        cursor.execute("SELECT `id`, `pname` FROM `issuetype`")
        it_names = {str(r["id"]): r["pname"] for r in cursor.fetchall()}
        for wf_name in sorted(workflow_to_issue_types.keys()):
            cursor.execute(
                f"SELECT `{desc_col}` AS descriptor FROM `jiraworkflows` WHERE `{wf_name_col}` = %s",
                (wf_name,),
            )
            row = cursor.fetchone()
            descriptor = (row.get("descriptor") or "").strip() if row else ""
            issue_types = workflow_to_issue_types[wf_name]
            issue_type_names = [it_names.get(str(i), i) if i != "(default)" else "(default)" for i in issue_types]
            parsed = _parse_workflow_descriptor_xml(descriptor) if descriptor else None
            result["workflows"].append({
                "workflow_name": wf_name,
                "issue_types": issue_type_names,
                "steps": parsed.get("steps", []) if parsed and not parsed.get("parse_error") else [],
                "transitions": parsed.get("transitions", []) if parsed and not parsed.get("parse_error") else [],
                "descriptor_xml": descriptor[:100000] if descriptor else None,
                "parse_error": parsed.get("parse_error") if parsed else False,
            })
        return result
    except Exception:
        if DEBUG:
            import traceback
            traceback.print_exc()
        return None


def fetch_automation_rules(cursor, project_id):
    """Extracts Automation rules: name, state, project scope (specific vs shared), author/owner name, actor name."""
    # Subquery: project count per rule (1 = project-specific, >1 = shared)
    # Left join app_user to resolve AUTHOR_KEY/ACTOR_KEY to usernames (Jira DC)
    query = (
        "SELECT r.`NAME`, r.`STATE`, r.`AUTHOR_KEY`, r.`ACTOR_KEY`, "
        "COALESCE(pc.`project_count`, 0) AS project_count, "
        "author.`lower_user_name` AS author_name, actor.`lower_user_name` AS actor_name "
        "FROM `ao_589059_rule_config` r "
        "JOIN `ao_589059_rule_cfg_proj_assoc` a ON r.`ID` = a.`RULE_CONFIG_ID` "
        "LEFT JOIN ("
        "  SELECT `RULE_CONFIG_ID`, COUNT(DISTINCT `PROJECT_ID`) AS project_count "
        "  FROM `ao_589059_rule_cfg_proj_assoc` GROUP BY `RULE_CONFIG_ID`"
        ") pc ON r.`ID` = pc.`RULE_CONFIG_ID` "
        "LEFT JOIN `app_user` author ON r.`AUTHOR_KEY` = author.`user_key` "
        "LEFT JOIN `app_user` actor ON r.`ACTOR_KEY` = actor.`user_key` "
        "WHERE a.`PROJECT_ID` = %s"
    )
    try:
        cursor.execute(query, (project_id,))
        rows = cursor.fetchall()
        out = []
        for r in rows:
            pc = r.get("project_count")
            if pc is not None and hasattr(pc, "__int__"):
                pc = int(pc)
            scope = "Project-specific" if pc == 1 else (f"Shared ({pc} projects)" if pc and pc > 1 else "—")
            author_name = (r.get("author_name") or r.get("AUTHOR_KEY") or r.get("author_key") or "").strip() or "—"
            actor_name = (r.get("actor_name") or r.get("ACTOR_KEY") or r.get("actor_key") or "").strip() or "—"
            out.append({
                "NAME": r.get("NAME"),
                "STATE": r.get("STATE"),
                "SCOPE": scope,
                "RULE_OWNER": author_name,
                "RULE_ACTOR": actor_name,
            })
        return out
    except Exception:
        # Fallback: no author/actor/scope columns or different schema
        try:
            query_fb = (
                "SELECT r.`NAME`, r.`STATE`, r.`AUTHOR_KEY`, r.`ACTOR_KEY`, "
                "COALESCE(pc.`project_count`, 0) AS project_count "
                "FROM `ao_589059_rule_config` r "
                "JOIN `ao_589059_rule_cfg_proj_assoc` a ON r.`ID` = a.`RULE_CONFIG_ID` "
                "LEFT JOIN ("
                "  SELECT `RULE_CONFIG_ID`, COUNT(DISTINCT `PROJECT_ID`) AS project_count "
                "  FROM `ao_589059_rule_cfg_proj_assoc` GROUP BY `RULE_CONFIG_ID`"
                ") pc ON r.`ID` = pc.`RULE_CONFIG_ID` "
                "WHERE a.`PROJECT_ID` = %s"
            )
            cursor.execute(query_fb, (project_id,))
            rows = cursor.fetchall()
            out = []
            for r in rows:
                pc = r.get("project_count")
                if pc is not None and hasattr(pc, "__int__"):
                    pc = int(pc)
                scope = "Project-specific" if pc == 1 else (f"Shared ({pc} projects)" if pc and pc > 1 else "—")
                author_name = (r.get("AUTHOR_KEY") or r.get("author_key") or "").strip() or "—"
                actor_name = (r.get("ACTOR_KEY") or r.get("actor_key") or "").strip() or "—"
                out.append({
                    "NAME": r.get("NAME"),
                    "STATE": r.get("STATE"),
                    "SCOPE": scope,
                    "RULE_OWNER": author_name,
                    "RULE_ACTOR": actor_name,
                })
            return out
        except Exception:
            # Minimal fallback: no project_count or author/actor
            try:
                cursor.execute(
                    "SELECT r.`NAME`, r.`STATE` FROM `ao_589059_rule_config` r "
                    "JOIN `ao_589059_rule_cfg_proj_assoc` a ON r.`ID` = a.`RULE_CONFIG_ID` "
                    "WHERE a.`PROJECT_ID` = %s",
                    (project_id,),
                )
                rows = cursor.fetchall()
                return [{"NAME": r.get("NAME"), "STATE": r.get("STATE"), "SCOPE": "—", "RULE_OWNER": "—", "RULE_ACTOR": "—"} for r in rows]
            except Exception:
                return []

def _col_has(tables_cols, table, *names):
    """Case-insensitive check: table has any of these column names."""
    c = tables_cols.get(table, set())
    return any(n.upper() in {x.upper() for x in c} for n in names)


def _discover_sr_prefixes_and_tables(cursor):
    """
    Discover ScriptRunner app key and table names. Uses case-insensitive
    column matching. Returns list of (profile_table, detail_table, mapping_tables).
    """
    # Fetch all columns for all ao_ tables (no filter) so we get actual names and case
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND LOWER(TABLE_NAME) LIKE 'ao_%%'
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """)
    rows = cursor.fetchall()
    tables_cols = {}
    for r in rows:
        t = r['TABLE_NAME']
        if t not in tables_cols:
            tables_cols[t] = set()
        tables_cols[t].add(r['COLUMN_NAME'])

    # Get unique prefixes (ao_XXXXXX)
    prefixes = set()
    for t in tables_cols:
        parts = t.split('_')
        if len(parts) >= 2 and parts[0].lower() == 'ao':
            prefixes.add(parts[0].lower() + '_' + parts[1].lower())

    result = []
    for prefix in sorted(prefixes):
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND LOWER(TABLE_NAME) LIKE %s
            ORDER BY TABLE_NAME
        """, (prefix + '%',))
        pref_tables = [r['TABLE_NAME'] for r in cursor.fetchall()]

        # Profile: has ID, NAME, no PROFILE_ID; prefer table name containing "profile"
        profile_t = None
        profile_candidates = []
        for t in pref_tables:
            if _col_has(tables_cols, t, 'ID') and _col_has(tables_cols, t, 'NAME') and not _col_has(tables_cols, t, 'PROFILE_ID'):
                profile_candidates.append((t, 'profile' in t.lower()))
        if profile_candidates:
            profile_candidates.sort(key=lambda x: (not x[1], x[0]))
            profile_t = profile_candidates[0][0]
        # Detail: has PROFILE_ID, ID, and (NAME or DESCRIPTION)
        detail_t = None
        candidates = []
        for t in pref_tables:
            if _col_has(tables_cols, t, 'PROFILE_ID') and _col_has(tables_cols, t, 'ID') and _col_has(tables_cols, t, 'NAME', 'DESCRIPTION'):
                if 'm_' not in t.lower() or 'detail' in t.lower():
                    candidates.append((t, 'detail' in t.lower()))
        if candidates:
            candidates.sort(key=lambda x: (not x[1], x[0]))
            detail_t = candidates[0][0]
        if not detail_t:
            for t in pref_tables:
                if 'it_detail' in t.lower() and _col_has(tables_cols, t, 'PROFILE_ID') and _col_has(tables_cols, t, 'ID'):
                    detail_t = t
                    break
        # Mapping: table that links detail to project. Either:
        # - DETAIL_ID + (PROJECT_ID or PROJECT_KEY), or
        # - TEMPLATE_ID + (PROJECT_ID or PROJECT_KEY) [e.g. ao_33a75d_it_default], or
        # - TEMPLATE_DETAIL_ID + TYPE + VALUE [e.g. ao_33a75d_it_context: TYPE=1 project key, TYPE=2 project id]
        mapping_tables = []
        for t in pref_tables:
            has_project = _col_has(tables_cols, t, 'PROJECT_ID', 'PROJECT_KEY')
            has_detail_id = _col_has(tables_cols, t, 'DETAIL_ID')
            has_template_id = _col_has(tables_cols, t, 'TEMPLATE_ID')
            has_template_detail_id = _col_has(tables_cols, t, 'TEMPLATE_DETAIL_ID')
            has_type_value = _col_has(tables_cols, t, 'TYPE') and _col_has(tables_cols, t, 'VALUE')
            if has_project and (has_detail_id or has_template_id):
                mapping_tables.append((t, 'DETAIL_ID' if has_detail_id else 'TEMPLATE_ID'))
            elif has_template_detail_id and has_type_value:
                mapping_tables.append((t, 'CONTEXT'))  # special: join on TEMPLATE_DETAIL_ID, filter TYPE/VALUE

        if profile_t and detail_t and mapping_tables:
            result.append((profile_t, detail_t, mapping_tables))

    return result


def _get_actual_column(cursor, table, *candidate_names):
    """Return actual column name for table (case-insensitive match), or None."""
    cursor.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
    """, (table,))
    actual = {r['COLUMN_NAME'].upper(): r['COLUMN_NAME'] for r in cursor.fetchall()}
    for n in candidate_names:
        if n.upper() in actual:
            return actual[n.upper()]
    return None


def _sr_mapping_counts(cursor, mt, link_col_name, link_col, detail_ids, is_context, m_type_col):
    """
    Return per-detail_id mapping counts: project_count, issuetype_count (for context table), optional field_count.
    detail_ids: list of detail ids; link_col: actual column name in mt (e.g. TEMPLATE_DETAIL_ID or DETAIL_ID).
    Returns dict: detail_id -> {project_count, issuetype_count, field_count?}.
    """
    if not detail_ids or not link_col:
        return {}
    detail_ids = [d for d in detail_ids if d is not None]
    if not detail_ids:
        return {}
    out = {}
    try:
        if is_context and m_type_col:
            # CONTEXT: TYPE=1 project key, TYPE=2 project id; TYPE=3 often issuetype
            placeholders = ",".join(["%s"] * len(detail_ids))
            cursor.execute(
                f"SELECT `{link_col}` AS did, `{m_type_col}` AS typ, COUNT(*) AS cnt "
                f"FROM `{mt}` WHERE `{link_col}` IN ({placeholders}) GROUP BY `{link_col}`, `{m_type_col}`",
                tuple(detail_ids),
            )
            for r in cursor.fetchall():
                did, typ, cnt = r.get("did"), r.get("typ"), int(r.get("cnt") or 0)
                if did not in out:
                    out[did] = {"project_count": 0, "issuetype_count": 0, "field_count": 0}
                if typ in (1, 2, "1", "2"):
                    out[did]["project_count"] = out[did].get("project_count", 0) + cnt
                elif typ in (3, "3"):
                    out[did]["issuetype_count"] = out[did].get("issuetype_count", 0) + cnt
                elif typ in (4, "4"):
                    out[did]["field_count"] = out[did].get("field_count", 0) + cnt
            for did in detail_ids:
                if did not in out:
                    out[did] = {"project_count": 0, "issuetype_count": 0, "field_count": 0}
        else:
            # Regular mapping: count rows per detail_id (project mappings)
            placeholders = ",".join(["%s"] * len(detail_ids))
            cursor.execute(
                f"SELECT `{link_col}` AS did, COUNT(*) AS cnt FROM `{mt}` WHERE `{link_col}` IN ({placeholders}) GROUP BY `{link_col}`",
                tuple(detail_ids),
            )
            for r in cursor.fetchall():
                did, cnt = r.get("did"), int(r.get("cnt") or 0)
                out[did] = {"project_count": cnt, "issuetype_count": 0, "field_count": None}
            for did in detail_ids:
                if did not in out:
                    out[did] = {"project_count": 0, "issuetype_count": 0, "field_count": None}
    except Exception:
        for did in detail_ids:
            out[did] = {"project_count": None, "issuetype_count": None, "field_count": None}
    return out


def fetch_sr_behaviors(cursor, project_id, project_key):
    """
    Extract ScriptRunner Behaviours that apply to this project.
    Discovers actual AO_ prefix and table names at runtime; uses actual DB column names in queries.
    Returns list of {NAME, DESCRIPTION, detail_id?, PROJECT_MAPPING_COUNT?, ISSUETYPE_MAPPING_COUNT?, FIELD_MAPPING_COUNT?}.
    """
    try:
        discovered = _discover_sr_prefixes_and_tables(cursor)
    except Exception as e:
        if DEBUG:
            sys.stderr.write(f"[SR] Discovery error: {e}\n")
        discovered = []

    if DEBUG:
        sys.stderr.write(f"[SR] Discovered {len(discovered)} prefix(s) with profile+detail+mapping\n")
        for pt, dt, mts in discovered:
            sys.stderr.write(f"     profile={pt} detail={dt} mapping={mts}\n")
        if not discovered:
            # Dump ao_ tables and their columns that look relevant so we can see actual schema
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND LOWER(TABLE_NAME) LIKE 'ao_%%'
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """)
            rows = cursor.fetchall()
            by_table = {}
            for r in rows:
                t = r['TABLE_NAME']
                if t not in by_table:
                    by_table[t] = []
                by_table[t].append(r['COLUMN_NAME'])
            want = ('ID', 'NAME', 'DESCRIPTION', 'PROFILE_ID', 'DETAIL_ID', 'PROJECT_ID', 'PROJECT_KEY', 'TARGET_PROJECT', 'BEHAVIOUR', 'BEHAVIOR')
            for t in sorted(by_table.keys()):
                cols = by_table[t]
                has_any = [c for c in cols if any(c.upper().startswith(w) or w in c.upper() for w in want)]
                if has_any:
                    sys.stderr.write(f"[SR] Table {t}: {has_any[:12]}\n")

    seen = set()
    result = []

    for profile_t, detail_t, mapping_tables in discovered:
        # Resolve actual column names for profile and detail (MySQL may use different case)
        p_id = _get_actual_column(cursor, profile_t, 'ID')
        p_name = _get_actual_column(cursor, profile_t, 'NAME')
        d_id = _get_actual_column(cursor, detail_t, 'ID')
        d_profile_id = _get_actual_column(cursor, detail_t, 'PROFILE_ID')
        d_desc = _get_actual_column(cursor, detail_t, 'DESCRIPTION')
        if not all([p_id, p_name, d_id, d_profile_id]):
            if DEBUG:
                sys.stderr.write(f"[SR] Skip {profile_t}/{detail_t}: missing ID/NAME/PROFILE_ID\n")
            continue

        for mt_item in mapping_tables:
            if isinstance(mt_item, tuple):
                mt, link_col_name = mt_item  # 'DETAIL_ID', 'TEMPLATE_ID', or 'CONTEXT'
            else:
                mt = mt_item
                link_col_name = 'DETAIL_ID'
            try:
                if link_col_name == 'CONTEXT':
                    # Context table: TEMPLATE_DETAIL_ID + TYPE + VALUE (TYPE=1 project key, TYPE=2 project id)
                    m_tpl_detail = _get_actual_column(cursor, mt, 'TEMPLATE_DETAIL_ID')
                    m_type = _get_actual_column(cursor, mt, 'TYPE')
                    m_value = _get_actual_column(cursor, mt, 'VALUE')
                    if not all([m_tpl_detail, m_type, m_value]):
                        continue
                    desc_sel = f"d.`{d_desc}`" if d_desc else "NULL"
                    q = f"""
                    SELECT DISTINCT p.`{p_name}` AS NAME, {desc_sel} AS DESCRIPTION, d.`{d_id}` AS detail_id
                    FROM `{profile_t}` p
                    JOIN `{detail_t}` d ON (p.`{p_id}` = d.`{d_profile_id}` OR CAST(p.`{p_id}` AS CHAR) = d.`{d_profile_id}`)
                    JOIN `{mt}` m ON d.`{d_id}` = m.`{m_tpl_detail}`
                    WHERE (m.`{m_type}` = '2' AND m.`{m_value}` = %s) OR (m.`{m_type}` = '1' AND m.`{m_value}` = %s)
                    """
                    cursor.execute(q, (str(project_id), project_key))
                else:
                    m_link_col = _get_actual_column(cursor, mt, link_col_name)
                    m_project_id = _get_actual_column(cursor, mt, 'PROJECT_ID')
                    m_project_key = _get_actual_column(cursor, mt, 'PROJECT_KEY')
                    if not m_link_col or (not m_project_id and not m_project_key):
                        continue
                    conditions = []
                    p_list = []
                    if m_project_id:
                        conditions.append(f"m.`{m_project_id}` = %s")
                        p_list.append(project_id)
                    if m_project_key:
                        conditions.append(f"m.`{m_project_key}` = %s")
                        p_list.append(project_key)
                    where_m = " OR ".join(conditions)
                    name_sel = f"p.`{p_name}`"
                    desc_sel = f"d.`{d_desc}`" if d_desc else "NULL"
                    q = f"""
                    SELECT DISTINCT {name_sel} AS NAME, {desc_sel} AS DESCRIPTION, d.`{d_id}` AS detail_id
                    FROM `{profile_t}` p
                    JOIN `{detail_t}` d ON (p.`{p_id}` = d.`{d_profile_id}` OR CAST(p.`{p_id}` AS CHAR) = d.`{d_profile_id}`)
                    JOIN `{mt}` m ON d.`{d_id}` = m.`{m_link_col}`
                    WHERE {where_m}
                    """
                    cursor.execute(q, tuple(p_list))
                rows = cursor.fetchall()
                if DEBUG and not rows:
                    sys.stderr.write(f"[SR] Query returned 0 rows: profile={profile_t} detail={detail_t} mapping={mt}\n")
                # Compute project/issuetype mapping counts per behavior (detail_id)
                count_by_detail = _sr_mapping_counts(cursor, mt, link_col_name, m_link_col if link_col_name != 'CONTEXT' else m_tpl_detail, [r.get('detail_id') for r in rows if r.get('detail_id') is not None], link_col_name == 'CONTEXT', m_type if link_col_name == 'CONTEXT' else None)
                for row in rows:
                    # Skip nameless behaviors (e.g. default/empty profile) to avoid confusing ghost rows
                    name_val = row.get('NAME')
                    if name_val is None or (isinstance(name_val, str) and not name_val.strip()):
                        continue
                    key = (row['NAME'], (row.get('DESCRIPTION') or ''))
                    if key not in seen:
                        seen.add(key)
                        did = row.get('detail_id')
                        rec = dict(row)
                        counts = count_by_detail.get(did) if isinstance(count_by_detail.get(did), dict) else {}
                        rec['PROJECT_MAPPING_COUNT'] = counts.get('project_count') if counts.get('project_count') is not None else None
                        rec['ISSUETYPE_MAPPING_COUNT'] = counts.get('issuetype_count') if counts.get('issuetype_count') is not None else None
                        rec['FIELD_MAPPING_COUNT'] = counts.get('field_count')
                        result.append(rec)
                if result:
                    return result
            except Exception as e:
                if DEBUG:
                    sys.stderr.write(f"[SR] Query error ({profile_t}/{detail_t}/{mt}): {e}\n")
                continue

        # Also try detail.PROJECT_KEY / detail.TARGET_PROJECT (behavior scoped directly on detail)
        try:
            d_pkey = _get_actual_column(cursor, detail_t, 'PROJECT_KEY')
            d_tgt = _get_actual_column(cursor, detail_t, 'TARGET_PROJECT')
            detail_proj_cols = [c for c in (d_pkey, d_tgt) if c]
            if detail_proj_cols:
                conds = [f"d.`{c}` = %s" for c in detail_proj_cols]
                where_d = " OR ".join(conds)
                desc_sel = f"d.`{d_desc}`" if d_desc else "NULL"
                q = f"""
                SELECT DISTINCT p.`{p_name}` AS NAME, {desc_sel} AS DESCRIPTION
                FROM `{profile_t}` p
                JOIN `{detail_t}` d ON (p.`{p_id}` = d.`{d_profile_id}` OR CAST(p.`{p_id}` AS CHAR) = d.`{d_profile_id}`)
                WHERE {where_d}
                """
                cursor.execute(q, tuple([project_key] * len(detail_proj_cols)))
                for row in cursor.fetchall():
                    # Skip nameless behaviors to avoid confusing ghost rows
                    name_val = row.get('NAME')
                    if name_val is None or (isinstance(name_val, str) and not name_val.strip()):
                        continue
                    key = (row['NAME'], (row.get('DESCRIPTION') or ''))
                    if key not in seen:
                        seen.add(key)
                        result.append(row)
                if result:
                    return result
        except Exception as e:
            if DEBUG:
                sys.stderr.write(f"[SR] Detail-scope query error: {e}\n")

    return result


def _fetch_sr_behavior_name(base_url, bearer_token, config_uuid):
    """GET single behaviour config XML and return name attribute from <config name=\"...\">."""
    base = base_url.rstrip("/")
    url = base + "/rest/scriptrunner/behaviours/latest/config/" + config_uuid
    req = Request(url, headers={"Authorization": "Bearer " + bearer_token.strip()})
    try:
        with urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                return None
            body = resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, OSError):
        return None
    try:
        root = ET.fromstring(body)
        name = root.get("name") or root.get("id")
        return (name or config_uuid[:8]).strip()
    except ET.ParseError:
        return None


def fetch_sr_behaviors_via_api(base_url, bearer_token, project_id, fetch_names=True):
    """
    Optional fallback: get ScriptRunner behaviours from REST API when DB returns none.
    Parses the full list XML to get config UUIDs for the project and per-config project/issuetype
    mapping counts; optionally fetches each config XML to get behaviour name.
    Returns (list of {NAME, DESCRIPTION, PROJECT_MAPPING_COUNT?, ISSUETYPE_MAPPING_COUNT?}, count).
    """
    base = base_url.rstrip("/")
    url = base + "/rest/scriptrunner/behaviours/latest/config"
    req = Request(url, headers={"Authorization": "Bearer " + bearer_token.strip()})
    try:
        with urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                return [], 0
            body = resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, OSError) as e:
        if DEBUG:
            sys.stderr.write(f"[SR API] Request error: {e}\n")
        return [], 0
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        if DEBUG:
            sys.stderr.write(f"[SR API] XML parse error: {e}\n")
        return [], 0
    # Build per-config mapping counts from full list XML (all projects)
    config_projects = {}   # config_uuid -> set of pid
    config_issuetypes = {} # config_uuid -> list of (pid, issuetype_id) for count
    for proj in root.findall(".//project"):
        pid = proj.get("pid")
        if not pid:
            continue
        proj_cfg = proj.get("configuration")
        if proj_cfg:
            config_projects.setdefault(proj_cfg, set()).add(pid)
            config_issuetypes.setdefault(proj_cfg, []).append((pid, None))
        for it in proj.findall("issuetype"):
            cfg = it.get("configuration")
            it_id = it.get("id")
            if cfg:
                config_projects.setdefault(cfg, set()).add(pid)
                config_issuetypes.setdefault(cfg, []).append((pid, it_id))
    pid_str = str(project_id)
    configs = set()
    for proj in root.findall(".//project"):
        if proj.get("pid") == pid_str:
            proj_cfg = proj.get("configuration")
            if proj_cfg:
                configs.add(proj_cfg)
            for it in proj.findall("issuetype"):
                cfg = it.get("configuration")
                if cfg:
                    configs.add(cfg)
    count = len(configs)
    if count == 0:
        return [], 0
    result = []
    if fetch_names and configs:
        seen_names = set()
        for cfg in sorted(configs):
            name = _fetch_sr_behavior_name(base_url, bearer_token, cfg)
            if name and name not in seen_names:
                seen_names.add(name)
                rec = {"NAME": name, "DESCRIPTION": f"Config: {cfg[:8]}…"}
                rec["PROJECT_MAPPING_COUNT"] = len(config_projects.get(cfg, set()))
                rec["ISSUETYPE_MAPPING_COUNT"] = len(config_issuetypes.get(cfg, []))
                result.append(rec)
        if not result:
            result = [{"NAME": "ScriptRunner (REST API)", "DESCRIPTION": f"{count} behaviour(s) applied to this project", "PROJECT_MAPPING_COUNT": None, "ISSUETYPE_MAPPING_COUNT": None}]
    else:
        # One placeholder; we still have per-config counts if we had built configs list with counts
        result = [{"NAME": "ScriptRunner (REST API)", "DESCRIPTION": f"{count} behaviour(s) applied to this project", "PROJECT_MAPPING_COUNT": None, "ISSUETYPE_MAPPING_COUNT": None}]
    return result, count


def fetch_permission_details(cursor, project_key):
    """Retrieves exact actors (Groups/Users) within the permission scheme."""
    query = (
        "SELECT sp.`permission_key`, sp.`perm_type`, sp.`perm_parameter` "
        "FROM `schemepermissions` sp WHERE sp.`scheme` = ("
        "SELECT `sink_node_id` FROM `nodeassociation` "
        "WHERE `source_node_id` = (SELECT `ID` FROM `project` WHERE `pkey` = %s) "
        "AND `sink_node_entity` = 'PermissionScheme') "
        "ORDER BY sp.`permission_key`"
    )
    cursor.execute(query, (project_key,))
    return cursor.fetchall()

def fetch_field_scope_counts(cursor):
    """
    For each fieldidentifier that appears on any screen, return how many distinct projects
    and how many distinct issue types use it (so admins can assess impact).
    Returns (dict: field_id -> {project_count, issue_type_count}, total_project_count).
    """
    total_projects = 0
    try:
        cursor.execute("SELECT COUNT(*) AS cnt FROM `project`")
        row = cursor.fetchone()
        total_projects = int(row["cnt"]) if row and row.get("cnt") is not None else 0
    except Exception:
        pass
    counts = {}
    query = (
        "SELECT fsli.`fieldidentifier` AS field_id, "
        "COUNT(DISTINCT p.`id`) AS project_count, "
        "COUNT(DISTINCT COALESCE(itsse.`issuetype`, -1)) AS issue_type_count "
        "FROM `fieldscreenlayoutitem` fsli "
        "JOIN `fieldscreentab` fst ON fsli.`fieldscreentab` = fst.`id` "
        "JOIN `fieldscreen` fs ON fst.`fieldscreen` = fs.`id` "
        "JOIN `fieldscreenschemeitem` fssi ON fs.`id` = fssi.`fieldscreen` "
        "JOIN `fieldscreenscheme` fss ON fssi.`fieldscreenscheme` = fss.`id` "
        "JOIN `issuetypescreenschemeentity` itsse ON fss.`id` = itsse.`fieldscreenscheme` "
        "JOIN `issuetypescreenscheme` itss ON itsse.`scheme` = itss.`id` "
        "JOIN `nodeassociation` na ON itss.`id` = na.`sink_node_id` AND na.`sink_node_entity` = 'IssueTypeScreenScheme' "
        "JOIN `project` p ON na.`source_node_id` = p.`id` "
        "GROUP BY fsli.`fieldidentifier`"
    )
    try:
        cursor.execute(query)
        for row in cursor.fetchall():
            fid = (row.get("field_id") or "").strip()
            if fid:
                pc = row.get("project_count")
                itc = row.get("issue_type_count")
                counts[fid] = {
                    "project_count": int(pc) if pc is not None else None,
                    "issue_type_count": int(itc) if itc is not None else None,
                }
    except Exception:
        pass
    return counts, total_projects


# Standard Jira field identifiers -> display name (for screens_and_fields)
STANDARD_FIELD_NAMES = {
    "summary": "Summary", "description": "Description", "issuetype": "Issue Type",
    "priority": "Priority", "assignee": "Assignee", "reporter": "Reporter",
    "components": "Components", "fixVersions": "Fix Versions", "labels": "Labels",
    "attachment": "Attachment", "issuelinks": "Issue Links", "security": "Security",
    "environment": "Environment", "duedate": "Due Date", "timetracking": "Time Tracking",
    "parent": "Parent", "customfield_10002": "Epic Link", "status": "Status", "resolution": "Resolution",
}

def fetch_screens_and_fields(cursor, project_key):
    """Deep extraction: Issue Types -> Screens -> Tabs -> Fields, with field name and required/optional."""
    query = (
        "SELECT DISTINCT it.`pname` AS issue_type, fs.`name` AS screen_name, fst.`name` AS tab_name, "
        "fsli.`fieldidentifier` AS field_id, fst.`sequence` AS tab_sequence, fsli.`sequence` AS field_sequence, "
        "cf.`cfname` AS field_name_cf "
        "FROM `project` p "
        "JOIN `nodeassociation` na_itss ON p.`id` = na_itss.`source_node_id` AND na_itss.`sink_node_entity` = 'IssueTypeScreenScheme' "
        "JOIN `issuetypescreenscheme` itss ON na_itss.`sink_node_id` = itss.`id` "
        "JOIN `issuetypescreenschemeentity` itsse ON itss.`id` = itsse.`scheme` "
        "LEFT JOIN `issuetype` it ON itsse.`issuetype` = it.`id` "
        "JOIN `fieldscreenscheme` fss ON itsse.`fieldscreenscheme` = fss.`id` "
        "JOIN `fieldscreenschemeitem` fssi ON fss.`id` = fssi.`fieldscreenscheme` "
        "JOIN `fieldscreen` fs ON fssi.`fieldscreen` = fs.`id` "
        "JOIN `fieldscreentab` fst ON fs.`id` = fst.`fieldscreen` "
        "JOIN `fieldscreenlayoutitem` fsli ON fst.`id` = fsli.`fieldscreentab` "
        "LEFT JOIN `customfield` cf ON fsli.`fieldidentifier` = CONCAT('customfield_', cf.`id`) "
        "WHERE p.`pkey` = %s"
    )
    try:
        cursor.execute(query, (project_key,))
        rows = cursor.fetchall()
    except Exception:
        # fallback if customfield join fails (e.g. column name differs)
        query_fb = (
            "SELECT DISTINCT it.`pname` AS issue_type, fs.`name` AS screen_name, fst.`name` AS tab_name, "
            "fsli.`fieldidentifier` AS field_id, fst.`sequence` AS tab_sequence, fsli.`sequence` AS field_sequence "
            "FROM `project` p "
            "JOIN `nodeassociation` na_itss ON p.`id` = na_itss.`source_node_id` AND na_itss.`sink_node_entity` = 'IssueTypeScreenScheme' "
            "JOIN `issuetypescreenscheme` itss ON na_itss.`sink_node_id` = itss.`id` "
            "JOIN `issuetypescreenschemeentity` itsse ON itss.`id` = itsse.`scheme` "
            "LEFT JOIN `issuetype` it ON itsse.`issuetype` = it.`id` "
            "JOIN `fieldscreenscheme` fss ON itsse.`fieldscreenscheme` = fss.`id` "
            "JOIN `fieldscreenschemeitem` fssi ON fss.`id` = fssi.`fieldscreenscheme` "
            "JOIN `fieldscreen` fs ON fssi.`fieldscreen` = fs.`id` "
            "JOIN `fieldscreentab` fst ON fs.`id` = fst.`fieldscreen` "
            "JOIN `fieldscreenlayoutitem` fsli ON fst.`id` = fsli.`fieldscreentab` "
            "WHERE p.`pkey` = %s"
        )
        cursor.execute(query_fb, (project_key,))
        rows = cursor.fetchall()
        for r in rows:
            r["field_name_cf"] = None
    required_set = set()
    # Normalize required value: Jira/OfBiz may store as 1, '1', 'true', 't', true.
    def _is_required_value(v):
        if v is None:
            return False
        s = str(v).strip().lower()
        return s in ("1", "true", "t", "yes", "y")

    def _collect_required(rows, *keys):
        for row in rows:
            for k in keys:
                v = row.get(k)
                if v is not None:
                    s = str(v).strip()
                    if s:
                        required_set.add(s)
                        if s.isdigit():
                            required_set.add("customfield_" + s)
                    break

    # 1) FieldLayoutScheme: required/isrequired = 1 or 'true' (Jira/OfBiz may store boolean as string)
    for (entity_col, item_layout_col, req_col) in [
        ("fieldlayoutscheme", "layout", "required"),
        ("fieldlayoutscheme", "layout", "isrequired"),
        ("scheme", "fieldlayout", "required"),
        ("scheme", "fieldlayout", "isrequired"),
    ]:
        try:
            cursor.execute(f"""
                SELECT DISTINCT fli.`fieldidentifier`
                FROM `project` p
                JOIN `nodeassociation` na ON p.`id` = na.`source_node_id` AND na.`sink_node_entity` = 'FieldLayoutScheme'
                JOIN `fieldlayoutscheme` fls ON na.`sink_node_id` = fls.`id`
                JOIN `fieldlayoutschemeentity` flse ON fls.`id` = flse.`{entity_col}`
                JOIN `fieldlayout` fl ON flse.`fieldlayout` = fl.`id`
                JOIN `fieldlayoutitem` fli ON fl.`id` = fli.`{item_layout_col}`
                WHERE p.`pkey` = %s AND (fli.`{req_col}` = 1 OR LOWER(TRIM(COALESCE(fli.`{req_col}`,''))) IN ('true','t','1','yes'))
            """, (project_key,))
            _collect_required(cursor.fetchall(), "fieldidentifier")
            if required_set:
                break
        except Exception:
            continue
        if required_set:
            break

    # 2) Fallback: fetch all fieldlayoutitem rows and treat any truthy required/isrequired as Required
    if not required_set:
        for (entity_col, item_layout_col) in [("fieldlayoutscheme", "layout"), ("scheme", "fieldlayout")]:
            for req_col in ["required", "isrequired"]:
                try:
                    cursor.execute(f"""
                        SELECT DISTINCT fli.`fieldidentifier`, fli.`{req_col}` AS req_val
                        FROM `project` p
                        JOIN `nodeassociation` na ON p.`id` = na.`source_node_id` AND na.`sink_node_entity` = 'FieldLayoutScheme'
                        JOIN `fieldlayoutscheme` fls ON na.`sink_node_id` = fls.`id`
                        JOIN `fieldlayoutschemeentity` flse ON fls.`id` = flse.`{entity_col}`
                        JOIN `fieldlayout` fl ON flse.`fieldlayout` = fl.`id`
                        JOIN `fieldlayoutitem` fli ON fl.`id` = fli.`{item_layout_col}`
                        WHERE p.`pkey` = %s
                    """, (project_key,))
                    for row in cursor.fetchall():
                        if _is_required_value(row.get("req_val")):
                            fid = (row.get("fieldidentifier") or "").strip()
                            if fid:
                                required_set.add(fid)
                                if fid.isdigit():
                                    required_set.add("customfield_" + fid)
                    if required_set:
                        break
                except Exception:
                    continue
            if required_set:
                break

    # 3) FieldConfigScheme path (fieldconfigitem): try = 1 and string 'true', then fetch-all fallback
    for na_entity in ("FieldConfigScheme", "FieldConfigurationScheme"):
        if required_set:
            break
        for (entity_col, req_col) in [("fieldconfigscheme", "required"), ("fieldconfigscheme", "isrequired"), ("scheme", "required"), ("scheme", "isrequired")]:
            try:
                cursor.execute(f"""
                    SELECT DISTINCT fci.`fieldidentifier`
                    FROM `project` p
                    JOIN `nodeassociation` na ON p.`id` = na.`source_node_id` AND na.`sink_node_entity` = %s
                    JOIN `fieldconfigscheme` fcs ON na.`sink_node_id` = fcs.`id`
                    JOIN `fieldconfigschemeentity` fcse ON fcs.`id` = fcse.`{entity_col}`
                    JOIN `fieldconfig` fc ON fcse.`fieldconfig` = fc.`id`
                    JOIN `fieldconfigitem` fci ON fc.`id` = fci.`fieldconfig`
                    WHERE p.`pkey` = %s AND (fci.`{req_col}` = 1 OR LOWER(TRIM(COALESCE(fci.`{req_col}`,''))) IN ('true','t','1','yes'))
                """, (na_entity, project_key))
                _collect_required(cursor.fetchall(), "fieldidentifier")
                if required_set:
                    break
            except Exception:
                continue
        if not required_set:
            for (entity_col, req_col) in [("fieldconfigscheme", "required"), ("fieldconfigscheme", "isrequired"), ("scheme", "required"), ("scheme", "isrequired")]:
                try:
                    cursor.execute(f"""
                        SELECT DISTINCT fci.`fieldidentifier`, fci.`{req_col}` AS req_val
                        FROM `project` p
                        JOIN `nodeassociation` na ON p.`id` = na.`source_node_id` AND na.`sink_node_entity` = %s
                        JOIN `fieldconfigscheme` fcs ON na.`sink_node_id` = fcs.`id`
                        JOIN `fieldconfigschemeentity` fcse ON fcs.`id` = fcse.`{entity_col}`
                        JOIN `fieldconfig` fc ON fcse.`fieldconfig` = fc.`id`
                        JOIN `fieldconfigitem` fci ON fc.`id` = fci.`fieldconfig`
                        WHERE p.`pkey` = %s
                    """, (na_entity, project_key))
                    for row in cursor.fetchall():
                        if _is_required_value(row.get("req_val")):
                            fid = (row.get("fieldidentifier") or "").strip()
                            if fid:
                                required_set.add(fid)
                                if fid.isdigit():
                                    required_set.add("customfield_" + fid)
                    if required_set:
                        break
                except Exception:
                    continue
    scope_counts, total_projects = fetch_field_scope_counts(cursor)
    out = []
    for r in rows:
        fid = (r.get("field_id") or "").strip()
        name = r.get("field_name_cf") or STANDARD_FIELD_NAMES.get(fid) or fid or "—"
        req = "Required" if fid in required_set else "Optional"
        sc = scope_counts.get(fid) or {}
        pc = sc.get("project_count")
        itc = sc.get("issue_type_count")
        if pc is not None and total_projects > 0 and pc >= total_projects:
            project_scope_str = "All projects"
        elif pc is not None:
            project_scope_str = str(pc)
        else:
            project_scope_str = "—"
        issue_type_scope_str = str(itc) if itc is not None else "—"
        out.append({
            "issue_type": r.get("issue_type") or "",
            "screen_name": r.get("screen_name") or "",
            "tab_name": r.get("tab_name") or "",
            "field_id": fid,
            "field_name": name,
            "required": req,
            "tab_sequence": r.get("tab_sequence"),
            "field_sequence": r.get("field_sequence"),
            "field_project_scope": project_scope_str,
            "field_issue_type_scope": issue_type_scope_str,
        })
    return out

def fetch_cf_options(cursor, project_id):
    """Retrieves custom field options specifically mapped to this project context.
    Returns list of dicts with field_id (e.g. customfield_43231), cfname, option_id, customvalue for audit/comparison."""
    query = (
        "SELECT cf.`id` AS cf_id, cf.`cfname`, cfo.`id` AS option_id, cfo.`customvalue` FROM `customfield` cf "
        "JOIN `customfieldoption` cfo ON cf.`id` = cfo.`customfield` "
        "JOIN `configurationcontext` cc ON CONCAT('customfield_', cf.`id`) = cc.`customfield` "
        "WHERE cc.`project` = %s OR cc.`project` IS NULL"
    )
    try:
        cursor.execute(query, (project_id,))
        rows = cursor.fetchall()
        out = []
        for r in rows:
            cf_id = r.get("cf_id")
            field_id = ("customfield_" + str(cf_id)) if cf_id is not None else None
            out.append({
                "field_id": field_id,
                "cfname": (r.get("cfname") or "").strip() or None,
                "option_id": r.get("option_id"),
                "customvalue": (r.get("customvalue") or "").strip() or None,
            })
        return out
    except Exception:
        # Fallback without field_id/option_id if column names differ
        try:
            cursor.execute(
                "SELECT cf.`cfname`, cfo.`customvalue` FROM `customfield` cf "
                "JOIN `customfieldoption` cfo ON cf.`id` = cfo.`customfield` "
                "JOIN `configurationcontext` cc ON CONCAT('customfield_', cf.`id`) = cc.`customfield` "
                "WHERE cc.`project` = %s OR cc.`project` IS NULL",
                (project_id,),
            )
            return cursor.fetchall()
        except Exception:
            return []

## --- MAIN EXECUTION --- ##

def run_audit(config, instance, project):
    """
    Run the full audit for the given instance and project. Returns the snapshot dict.
    Raises on error (e.g. project not found, DB error). Caller must have loaded config.
    """
    conn = get_db_connection(config, instance)
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        pulse = fetch_project_pulse(cursor, project)
        if not pulse:
            raise ValueError(f"Project {project} not found.")
        snapshot = fetch_blueprint(cursor, project)
        sr_behaviors = fetch_sr_behaviors(cursor, pulse['ID'], project)
        sr_behaviors_count = len(sr_behaviors) if sr_behaviors else 0
        if not sr_behaviors:
            base_url = config.get(instance, "jira_base_url", fallback="")
            token = config.get(instance, "sr_bearer_token", fallback="")
            if base_url and token:
                sr_behaviors, sr_behaviors_count = fetch_sr_behaviors_via_api(base_url, token, pulse['ID'])
        last_issue = fetch_last_created_issue(cursor, pulse['ID'], project)
        last_updated = fetch_last_updated_issue(cursor, pulse['ID'], project)
        perm_details = fetch_permission_details(cursor, project)
        snapshot.update({
            "project_key": project,
            "project_name": pulse['pname'],
            "project_lead": pulse.get("lead"),
            "project_category": fetch_project_category(cursor, project),
            "default_assignee_type": fetch_default_assignee_type(cursor, project),
            "issue_type_scheme": fetch_issue_type_scheme_name(cursor, project),
            "issue_type_scheme_issue_types": fetch_issue_type_scheme_issue_types(cursor, project),
            "last_issue_key": last_issue.get("last_issue_key") if last_issue else None,
            "last_issue_created": last_issue.get("last_issue_created") if last_issue else None,
            "last_updated_issue_key": last_updated.get("last_updated_issue_key") if last_updated else None,
            "last_updated_issue_timestamp": last_updated.get("last_updated_issue_timestamp") if last_updated else None,
            "total_issue_count": fetch_total_issue_count(cursor, pulse['ID']),
            "issue_count_by_type": fetch_issue_count_by_type(cursor, pulse['ID'], project),
            "component_count": fetch_component_count(cursor, pulse['ID']),
            "components": fetch_components(cursor, pulse['ID']),
            "version_count": fetch_version_count(cursor, pulse['ID']),
            "versions": fetch_versions(cursor, pulse['ID']),
            "permission_entry_count": len(perm_details) if perm_details else 0,
            "automation_rules": fetch_automation_rules(cursor, pulse['ID']),
            "sr_behaviors": sr_behaviors,
            "sr_behaviors_count": sr_behaviors_count,
            "permission_details": perm_details,
            "screens_and_fields": fetch_screens_and_fields(cursor, project),
            "custom_field_options": fetch_cf_options(cursor, pulse['ID'])
        })
        wf_details = fetch_workflow_scheme_details(
            cursor, project,
            workflow_scheme_id=snapshot.get("workflow_scheme_id"),
            workflow_scheme_name=snapshot.get("workflow_scheme"),
        )
        if wf_details:
            snapshot["workflow_scheme_details"] = wf_details
            # Explicit mapping for comparison: issue_type -> workflow_name
            mapping = []
            for wf in (wf_details.get("workflows") or []):
                wf_name = wf.get("workflow_name") or ""
                for it in (wf.get("issue_types") or []):
                    display_issue_type = "(default)" if it in ("0", 0) else it
                    mapping.append({"issue_type": display_issue_type, "workflow_name": wf_name})
            snapshot["workflow_scheme_mapping"] = mapping
        else:
            snapshot["workflow_scheme_mapping"] = []
        enrich_snapshot_with_user_info(cursor, snapshot)
        return snapshot
    finally:
        cursor.close()
        conn.close()


def main():
    args = get_args()
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        snapshot = run_audit(config, args.instance, args.project)
        if args.summary:
            print(build_audit_summary(snapshot))
        print(json.dumps(snapshot, indent=4, default=json_serial))
    except Exception as e:
        sys.stderr.write(f"Fatal Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
