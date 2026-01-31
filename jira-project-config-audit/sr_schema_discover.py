#!/usr/bin/env python3
"""
Discover ScriptRunner Behaviours schema: find which AO_ tables hold behavior names
and how they link to projects.
Usage:
  python sr_schema_discover.py --instance SBX [--project UAT1ESX]       # full scan (slow)
  python sr_schema_discover.py --instance SBX --quick [--project UAT1ESX]  # quick (ScriptRunner/Automation prefixes only)
"""
import mysql.connector
import configparser
import argparse
import sys

# Prefixes to scan in --quick mode (ScriptRunner, Automation for Jira, etc.)
QUICK_PREFIXES = ('ao_33a75d', 'ao_4b00e6', 'ao_8ba09e')

def get_db(config, instance):
    s = config[instance]
    return mysql.connector.connect(
        host=s['host'], user=s['user'], password=s['password'],
        database=s['database'], port=s.getint('port', 3306)
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True, help="Instance from config.ini (e.g. SBX, PRD)")
    ap.add_argument("--project", default="UAT1ESX", help="Project key to find mappings for")
    ap.add_argument("--quick", action="store_true", help="Only scan likely ScriptRunner/Automation prefixes (ao_33a75d, ao_4b00e6, ao_8ba09e); finishes in seconds")
    args = ap.parse_args()

    config = configparser.ConfigParser()
    config.read('config.ini')
    conn = get_db(config, args.instance)
    cursor = conn.cursor(dictionary=True)

    # 1) List AO_ tables (optionally limited to --quick prefixes)
    if args.quick:
        ao_tables = []
        for prefix in QUICK_PREFIXES:
            cursor.execute("""
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND LOWER(TABLE_NAME) LIKE %s
                ORDER BY TABLE_NAME
            """, (prefix + '%',))
            ao_tables.extend(r['TABLE_NAME'] for r in cursor.fetchall())
        ao_tables = sorted(set(ao_tables))
        print(f"--- Quick mode: found {len(ao_tables)} AO_ tables (prefixes: {', '.join(QUICK_PREFIXES)}) ---\n")
    else:
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'ao_%%'
            ORDER BY TABLE_NAME
        """)
        ao_tables = [r['TABLE_NAME'] for r in cursor.fetchall()]
        print(f"--- Found {len(ao_tables)} AO_ tables (full scan) ---\n")

    # 2) Find project ID for UAT1ESX
    cursor.execute("SELECT id, pkey, pname FROM project WHERE pkey = %s", (args.project,))
    proj = cursor.fetchone()
    if not proj:
        print(f"Project {args.project} not found.")
        sys.exit(1)
    project_id, project_key, project_name = proj['id'], proj['pkey'], proj['pname']
    print(f"Project: {project_key} (id={project_id}, name={project_name})\n")

    # 3) Search for behavior name substring in any string column across ALL ao_ tables
    search_substrings = ["RCCA Required", "Build Numeric", "Metadata Field", "Making RCCA"]
    found_in_tables = {}  # table -> (column, sample_row)

    for table in ao_tables:
        try:
            cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))
            cols = cursor.fetchall()
            text_cols = [c['COLUMN_NAME'] for c in cols if c['DATA_TYPE'] in ('varchar', 'text', 'longtext', 'mediumtext')]
            if not text_cols:
                continue
            for sub in search_substrings:
                for col in text_cols:
                    try:
                        q = f"SELECT * FROM `{table}` WHERE `{col}` LIKE %s LIMIT 1"
                        cursor.execute(q, (f"%{sub}%",))
                        row = cursor.fetchone()
                        if row:
                            found_in_tables[table] = (col, dict(row))
                            break
                    except Exception:
                        pass
                if table in found_in_tables:
                    break
        except Exception as e:
            pass

    if not found_in_tables:
        print("No AO_ table contained any of the behavior name substrings. Trying LIKE '%Behaviour%' / '%Behavior%'...")
        for table in ao_tables:
            try:
                cursor.execute(f"DESCRIBE `{table}`")
                cols = [c['Field'] for c in cursor.fetchall()]
                for col in cols:
                    if 'NAME' not in col.upper() and 'DESC' not in col.upper():
                        continue
                    try:
                        cursor.execute(f"SELECT * FROM `{table}` WHERE `{col}` LIKE %s LIMIT 3", ("%Behaviour%",))
                        rows = cursor.fetchall()
                        if rows:
                            print(f"  Table {table} col {col}: sample = {rows[0]}")
                            found_in_tables[table] = (col, rows[0])
                            break
                    except Exception:
                        pass
                if table in found_in_tables:
                    break
            except Exception:
                pass

    print("--- Tables containing behavior-like names ---")
    for t, (col, row) in found_in_tables.items():
        print(f"  Table: {t}")
        print(f"  Column: {col}")
        print(f"  Sample keys in row: {list(row.keys())[:15]}")
        print(f"  Sample row (truncated): {str(row)[:300]}...")
        print()

    # 4) Derive prefix (e.g. ao_33a75d) and list tables with that prefix
    prefixes = set()
    for t in found_in_tables:
        # ao_XXXXXX_rest
        parts = t.split('_')
        if len(parts) >= 2 and parts[0].lower() == 'ao':
            prefix = '_'.join(parts[:2]).lower()  # ao_33a75d
            prefixes.add(prefix)
    print("--- Inferred ScriptRunner prefix(es) ---")
    for p in sorted(prefixes):
        print(f"  {p}")
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND LOWER(TABLE_NAME) LIKE %s
            ORDER BY TABLE_NAME
        """, (p + "%",))
        for r in cursor.fetchall():
            print(f"    - {r['TABLE_NAME']}")
    print()

    # 5) For each prefix, find tables that have DETAIL_ID or PROFILE_ID and PROJECT_ID or PROJECT_KEY
    print("--- Mapping tables (have DETAIL_ID or PROFILE_ID + PROJECT link) ---")
    for p in sorted(prefixes):
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND LOWER(TABLE_NAME) LIKE %s
            AND (COLUMN_NAME IN ('DETAIL_ID','PROFILE_ID','TEMPLATE_ID') OR COLUMN_NAME LIKE '%%PROJECT%%')
            ORDER BY TABLE_NAME, COLUMN_NAME
        """, (p + "%",))
        rows = cursor.fetchall()
        by_table = {}
        for r in rows:
            t = r['TABLE_NAME']
            if t not in by_table:
                by_table[t] = []
            by_table[t].append(r['COLUMN_NAME'])
        for t, cols in by_table.items():
            has_detail = 'DETAIL_ID' in cols or 'PROFILE_ID' in cols or 'TEMPLATE_ID' in cols
            has_proj = any('PROJECT' in c for c in cols)
            if has_detail and has_proj:
                print(f"  {t}: {cols}")
    print()

    # 6) Try to get behavior names linked to project: list all tables with PROJECT_ID or PROJECT_KEY
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'ao_%%'
        AND COLUMN_NAME IN ('PROJECT_ID', 'PROJECT_KEY', 'DETAIL_ID', 'PROFILE_ID', 'ID', 'NAME', 'DESCRIPTION')
        ORDER BY TABLE_NAME
    """)
    all_cols = cursor.fetchall()
    # Group by table
    tables_cols = {}
    for r in all_cols:
        t = r['TABLE_NAME']
        if t not in tables_cols:
            tables_cols[t] = set()
        tables_cols[t].add(r['COLUMN_NAME'])

    # Find detail-like table (has NAME or DESCRIPTION and PROFILE_ID or link to profile)
    detail_tables = [t for t, c in tables_cols.items() if ('NAME' in c or 'DESCRIPTION' in c) and ('PROFILE_ID' in c or 'ID' in c)]
    # Find profile-like table (has NAME)
    profile_tables = [t for t, c in tables_cols.items() if 'NAME' in c and 'ID' in c and 'PROFILE_ID' not in c]
    mapping_tables = [t for t, c in tables_cols.items() if 'DETAIL_ID' in c and ('PROJECT_ID' in c or 'PROJECT_KEY' in c)]

    print("--- Likely profile tables (NAME + ID): ---")
    for t in profile_tables[:20]:
        print(f"  {t}")
    print("--- Likely detail tables (NAME/DESC + PROFILE_ID): ---")
    for t in detail_tables[:20]:
        print(f"  {t}")
    print("--- Likely mapping tables (DETAIL_ID + PROJECT): ---")
    for t in mapping_tables[:20]:
        print(f"  {t}")

    # 7) Raw query: for each mapping table, find matching profile/detail tables (same prefix) and try query
    if prefixes and mapping_tables:
        for prefix in sorted(prefixes):
            # Tables with this prefix
            cursor.execute("""
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND LOWER(TABLE_NAME) LIKE %s
                ORDER BY TABLE_NAME
            """, (prefix + "%",))
            pref_tables = [r['TABLE_NAME'] for r in cursor.fetchall()]
            profile_t = next((t for t in pref_tables if 'profile' in t.lower() and 'it_' in t.lower()), None)
            detail_t = next((t for t in pref_tables if 'detail' in t.lower() and 'it_' in t.lower() and 'm_' not in t.lower()), None)
            if not profile_t or not detail_t:
                continue
            for mt in mapping_tables:
                if mt not in pref_tables:
                    continue
                try:
                    print(f"\n--- Trying: profile={profile_t}, detail={detail_t}, mapping={mt} ---")
                    q = f"""
                    SELECT DISTINCT p.NAME AS behavior_name, d.DESCRIPTION
                    FROM `{profile_t}` p
                    JOIN `{detail_t}` d ON (p.ID = d.PROFILE_ID OR CAST(p.ID AS CHAR) = d.PROFILE_ID)
                    JOIN `{mt}` m ON d.ID = m.DETAIL_ID
                    WHERE m.PROJECT_ID = %s OR m.PROJECT_KEY = %s
                    """
                    cursor.execute(q, (project_id, project_key))
                    rows = cursor.fetchall()
                    print(f"  Rows returned: {len(rows)}")
                    for row in rows[:10]:
                        print(f"    {row}")
                    if rows:
                        break
                except Exception as e:
                    print(f"  Error: {e}")
            else:
                continue
            break

    conn.close()

if __name__ == "__main__":
    main()
