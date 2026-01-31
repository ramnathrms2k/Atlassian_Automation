import json
import re
import sys

def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def get_names(data_list, key='NAME'):
    return {item[key] for item in data_list if isinstance(item, dict) and key in item}

def _sr_count_from_list(sr_list):
    """Derive ScriptRunner behaviour count: use sr_behaviors_count if in item, else parse DESCRIPTION 'N behaviour(s)', else len(names)."""
    if not sr_list or not isinstance(sr_list, list):
        return 0
    for item in sr_list:
        if isinstance(item, dict):
            desc = item.get("DESCRIPTION") or ""
            m = re.search(r"(\d+)\s+behaviour\(s\)", desc)
            if m:
                return int(m.group(1))
    return len(get_names(sr_list))

def main(file_sbx, file_prd):
    sbx = load_json(file_sbx)
    prd = load_json(file_prd)

    print(f"\n{'[ JIRA PROJECT CONFIG COMPARISON ]':^80}")
    print(f"{'PROJECT: ' + sbx['project_key']:^80}\n")
    print(f"{'CATEGORY':<25} | {'SANDBOX (SBX)':<25} | {'PRODUCTION (PRD)':<25}")
    print("-" * 80)

    # 1. Scheme Comparison
    for k in ['workflow_scheme', 'permission_scheme', 'notification_scheme']:
        s_val, p_val = str(sbx.get(k)), str(prd.get(k))
        mark = " [!] DIFF" if s_val != p_val else ""
        print(f"{k.replace('_',' ').title():<25} | {s_val[:25]:<25} | {p_val[:25]:<25}{mark}")

    # 2. Automation Rules Delta
    s_rules = get_names(sbx.get('automation_rules', []))
    p_rules = get_names(prd.get('automation_rules', []))
    
    print(f"{'Automation Rules':<25} | {len(s_rules):<25} | {len(p_rules):<25}")
    if p_rules - s_rules:
        print(f"\n[!] MISSING IN SANDBOX (PRD ONLY):")
        for r in (p_rules - s_rules): print(f"  - {r}")
    
    if s_rules - p_rules:
        print(f"\n[?] EXTRA IN SANDBOX (NOT IN PRD):")
        for r in (s_rules - p_rules): print(f"  - {r}")

    # 3. ScriptRunner Behaviors (use sr_behaviors_count when present, else parse DESCRIPTION or list length)
    s_count = sbx.get('sr_behaviors_count')
    p_count = prd.get('sr_behaviors_count')
    if s_count is None:
        s_count = _sr_count_from_list(sbx.get('sr_behaviors', []))
    if p_count is None:
        p_count = _sr_count_from_list(prd.get('sr_behaviors', []))
    print(f"\n{'ScriptRunner Behaviors':<25} | {s_count:<25} | {p_count:<25}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compare_audit.py sbx.json prd.json")
    else:
        main(sys.argv[1], sys.argv[2])
