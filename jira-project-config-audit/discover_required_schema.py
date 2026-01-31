#!/usr/bin/env python3
"""
Discover Jira DB schema for required-field detection.
Run: python discover_required_schema.py --instance PRD --project UAT1ESX
Use this if Screens and Fields still show all Optional; share the output to adapt queries.
"""
import argparse
import configparser
import os
import sys

# Same DB connection as jira_audit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jira_audit

def main():
    p = argparse.ArgumentParser(description="Discover field layout/config schema for required fields")
    p.add_argument("--instance", required=True, help="Instance from config.ini (e.g. PRD)")
    p.add_argument("--project", default="", help="Project key (optional, for nodeassociation check)")
    args = p.parse_args()
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), "config.ini"))
    if args.instance not in config:
        print(f"Unknown instance: {args.instance}")
        sys.exit(1)
    conn = jira_audit.get_db_connection(config, args.instance)
    cur = conn.cursor(dictionary=True)
    try:
        print("=== fieldlayoutitem ===")
        try:
            cur.execute("SHOW COLUMNS FROM fieldlayoutitem")
            for row in cur.fetchall():
                f, t = row.get("Field") or row.get("field"), row.get("Type") or row.get("type")
                print(" ", f, t)
        except Exception as e:
            print(" ", "Error:", e)
        print("\n=== fieldconfigitem ===")
        try:
            cur.execute("SHOW COLUMNS FROM fieldconfigitem")
            for row in cur.fetchall():
                f, t = row.get("Field") or row.get("field"), row.get("Type") or row.get("type")
                print(" ", f, t)
        except Exception as e:
            print(" ", "Error:", e)
        print("\n=== fieldlayoutschemeentity ===")
        try:
            cur.execute("SHOW COLUMNS FROM fieldlayoutschemeentity")
            for row in cur.fetchall():
                print(" ", row.get("Field"), row.get("Type"))
        except Exception as e:
            print(" ", "Error:", e)
        print("\n=== fieldconfigschemeentity ===")
        try:
            cur.execute("SHOW COLUMNS FROM fieldconfigschemeentity")
            for row in cur.fetchall():
                f, t = row.get("Field") or row.get("field"), row.get("Type") or row.get("type")
                print(" ", f, t)
        except Exception as e:
            print(" ", "Error:", e)
        print("\n=== nodeassociation SINK_NODE_ENTITY (project schemes) ===")
        try:
            cur.execute("""
                SELECT DISTINCT na.sink_node_entity
                FROM nodeassociation na
                JOIN project p ON p.id = na.source_node_id AND na.source_node_entity = 'Project'
                LIMIT 20
            """)
            for row in cur.fetchall():
                print(" ", row.get("sink_node_entity"))
        except Exception as e:
            print(" ", "Error:", e)
        if args.project:
            print(f"\n=== Sample required field layout items for project {args.project} ===")
            try:
                cur.execute("""
                    SELECT DISTINCT fli.fieldidentifier, fli.isrequired, fli.required
                    FROM project p
                    JOIN nodeassociation na ON p.id = na.source_node_id AND na.sink_node_entity = 'FieldLayoutScheme'
                    JOIN fieldlayoutscheme fls ON na.sink_node_id = fls.id
                    JOIN fieldlayoutschemeentity flse ON fls.id = flse.scheme
                    JOIN fieldlayout fl ON flse.fieldlayout = fl.id
                    JOIN fieldlayoutitem fli ON fl.id = fli.fieldlayout
                    WHERE p.pkey = %s
                    LIMIT 10
                """, (args.project,))
                rows = cur.fetchall()
                if rows:
                    for r in rows:
                        print(" ", r)
                else:
                    print("  (no rows - try scheme/fieldlayout or different entity column names)")
            except Exception as e:
                print("  Error (try other column names):", e)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
