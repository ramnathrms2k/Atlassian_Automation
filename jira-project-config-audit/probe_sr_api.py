#!/usr/bin/env python3
"""
Probe ScriptRunner Behaviours REST API: inspect list and single-config responses,
and derive project/issuetype mapping counts from the list XML.

Run from jira-project-config-audit dir (needs config.ini and jira_audit for project_id):

  python probe_sr_api.py --instance PRD --project UAT1ESX

Optional:
  --save-dir DIR   Save raw XML to DIR (default: current dir)
  --no-save        Only print summary, do not save XML files

Uses config.ini: [instance] jira_base_url, sr_bearer_token (or [DEFAULT] sr_bearer_token).
"""
import argparse
import configparser
import os
import sys
import xml.etree.ElementTree as ET

from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Same dir as this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.ini")


def get_config():
    cfg = configparser.ConfigParser()
    if not os.path.isfile(CONFIG_PATH):
        return None
    cfg.read(CONFIG_PATH)
    return cfg


def get_project_id(cursor, project_key):
    cursor.execute("SELECT `ID` FROM `project` WHERE `pkey` = %s", (project_key,))
    row = cursor.fetchone()
    return row["ID"] if row else None


def fetch_url(url, bearer_token, timeout=30):
    req = Request(url, headers={"Authorization": "Bearer " + bearer_token.strip()})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, OSError) as e:
        return None, str(e)


def main():
    ap = argparse.ArgumentParser(description="Probe ScriptRunner Behaviours API")
    ap.add_argument("--instance", required=True, help="Instance from config.ini (e.g. PRD, SBX)")
    ap.add_argument("--project", required=True, help="Project key (e.g. UAT1ESX)")
    ap.add_argument("--save-dir", default=SCRIPT_DIR, help="Directory to save raw XML (default: script dir)")
    ap.add_argument("--no-save", action="store_true", help="Do not save XML files, only print summary")
    args = ap.parse_args()

    config = get_config()
    if not config or args.instance not in config:
        print(f"Error: config.ini missing or instance [{args.instance}] not found.")
        sys.exit(1)

    base_url = config.get(args.instance, "jira_base_url", fallback="").strip()
    token = config.get(args.instance, "sr_bearer_token", fallback=config.get("DEFAULT", "sr_bearer_token", fallback="")).strip()
    if not base_url or not token:
        print("Error: jira_base_url and sr_bearer_token must be set for this instance.")
        sys.exit(1)

    base_url = base_url.rstrip("/")
    list_url = base_url + "/rest/scriptrunner/behaviours/latest/config"

    # Resolve project_id (optional, for summary)
    project_id = None
    try:
        import jira_audit
        conn = jira_audit.get_db_connection(config, args.instance)
        cur = conn.cursor(dictionary=True)
        project_id = get_project_id(cur, args.project)
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Note: could not get project_id from DB: {e}")

    print("=== 1. GET list (all project/issuetype → config mappings) ===")
    print(f"URL: {list_url}\n")
    status, body = fetch_url(list_url, token)
    if status != 200:
        print(f"Request failed: status={status}, error={body}")
        sys.exit(1)

    if not args.no_save:
        path = os.path.join(args.save_dir, "sr_config_list.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"Saved full response ({len(body)} chars) to: {path}")

    # Parse and summarize structure
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"XML parse error: {e}")
        sys.exit(1)

    tag = root.tag
    print(f"Root tag: {tag}")
    children = list(root)
    print(f"Direct children: {[c.tag for c in children]}")
    if children:
        first = children[0]
        print(f"First child tag: {first.tag}, attrs: {first.attrib}")

    # Build per-config counts from list XML
    # Two shapes: <project pid="..." configuration="UUID"/> (project-level) and <project pid="..."><issuetype id="..." configuration="UUID"/></project>
    config_projects = {}   # config_uuid -> set of project pid
    config_issuetypes = {} # config_uuid -> list of (pid, issuetype_id) for count
    projects_seen = set()
    for proj in root.findall(".//project"):
        pid = proj.get("pid")
        if pid:
            projects_seen.add(pid)
        # Project-level config (no issuetype children)
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

    print(f"\nParsed: {len(projects_seen)} project(s), {len(config_projects)} unique config UUID(s)")

    # Per-config project count and issuetype (mapping) count
    print("\n--- Per-config mapping counts (from list XML) ---")
    for cfg in sorted(config_projects.keys()):
        proj_count = len(config_projects[cfg])
        it_count = len(config_issuetypes.get(cfg, []))
        print(f"  {cfg[:12]}...  projects: {proj_count}, issuetype mappings: {it_count}")

    # Configs for the requested project (what we show in audit)
    pid_str = str(project_id) if project_id else None
    if pid_str:
        configs_for_project = set()
        for proj in root.findall(".//project"):
            if proj.get("pid") == pid_str:
                for it in proj.findall("issuetype"):
                    c = it.get("configuration")
                    if c:
                        configs_for_project.add(c)
        print(f"\nConfigs for project {args.project} (pid={pid_str}): {len(configs_for_project)}")
        for c in sorted(configs_for_project):
            print(f"  {c[:12]}...  -> project count: {len(config_projects.get(c, set()))}, issuetype count: {len(config_issuetypes.get(c, []))}")

    # 2. GET one single-config XML (first config for this project)
    if config_projects and (pid_str and configs_for_project or not pid_str):
        one_cfg = sorted(configs_for_project)[0] if pid_str and configs_for_project else sorted(config_projects.keys())[0]
        single_url = base_url + "/rest/scriptrunner/behaviours/latest/config/" + one_cfg
        print("\n=== 2. GET single config (structure probe) ===")
        print(f"URL: {single_url}\n")
        status2, body2 = fetch_url(single_url, token, timeout=15)
        if status2 == 200:
            if not args.no_save:
                path2 = os.path.join(args.save_dir, "sr_config_single.xml")
                with open(path2, "w", encoding="utf-8") as f:
                    f.write(body2)
                print(f"Saved ({len(body2)} chars) to: {path2}")
            try:
                root2 = ET.fromstring(body2)
                print(f"Root tag: {root2.tag}, attrs: {list(root2.attrib.keys())}")
                for c in list(root2):
                    print(f"  Child: <{c.tag}> attrs: {list(c.attrib.keys())}")
            except ET.ParseError:
                print("(Single config response is not XML or parse failed.)")
        else:
            print(f"Single config request failed: {status2} {body2[:200]}")

    print("\nDone. If list XML shows project/issuetype counts above, we can wire these into the API path in jira_audit.")


if __name__ == "__main__":
    main()
