# engine.py
import requests
import re
import datetime
import sys
# --- FIX: Added VRLI_HOST to imports ---
from config import BASE_URL, KNOWN_DEFINITIONS, PRESETS, VRLI_HOST

def discover_fields(token):
    sys.stderr.write("[*] Auto-Discovering Schema...\n")
    try:
        r = requests.get(f"{BASE_URL}/fields", headers={"Authorization":f"Bearer {token}", "Accept":"application/json"}, verify=False)
        field_map = {}
        for f in r.json():
            d_name = f.get("displayName")
            i_name = f.get("internalName")
            is_static = f.get("isStatic", False)
            
            if d_name and i_name:
                known = KNOWN_DEFINITIONS.get(d_name)
                if known:
                    core = known.get("customRegex") or PRESETS.get(known.get("regexPreset"), ".*")
                    pre, post = known.get("preContext", ""), known.get("postContext", "")
                    py_pattern = re.compile(known.get("pyRegex")) if known.get("pyRegex") else None
                else:
                    core = f.get("customRegex") or PRESETS.get(f.get("regexPreset"), ".*")
                    pre, post = f.get("preContext", ""), f.get("postContext", "")
                    py_pattern = None
                
                full_regex = f"{pre}(?<{i_name}>{core}){post}"
                field_map[d_name] = { "id": i_name, "type": f.get("fieldType", "STRING"), "piql_regex": full_regex, "original_name": d_name, "static": is_static, "py_pattern": py_pattern }
                field_map[d_name.lower()] = field_map[d_name]
        return field_map
    except Exception as e: sys.stderr.write(f"[-] Discovery Error: {e}\n"); return {}

def build_piql(start, end, filters, field_map):
    query_parts = [f"timestamp >= {start}", f"timestamp <= {end}"]
    for f_str in filters:
        match = re.match(r"^([\w\.]+)(>=|<=|!=|=|>|<)(.+)$", f_str)
        if not match: continue
        key, op, val = match.groups()
        info = field_map.get(key) or field_map.get(key.lower())
        
        if info:
            iid = info["id"]
            if info["static"]:
                neg = "NOT " if op == "!=" else ""
                query_parts.append(f'{neg}{iid}:"{val}"')
            else:
                safe_regex = info["piql_regex"].replace('"', '\\"')
                if info["type"] == "NUMBER" and op in [">", "<", ">=", "<="]:
                     query_parts.append(f'(text=~"{safe_regex}" AND {iid}{op}{val})')
                else:
                    neg = "NOT " if op == "!=" else ""
                    query_parts.append(f'(text=~"{safe_regex}" AND {neg}{iid}:"{val}")')
        else:
            if key == "apptag": query_parts.append(f'apptag:"{val}"')
            else: query_parts.append(f'text:"{val}"')
    return f"SELECT item0 FROM {' AND '.join(query_parts)} as item0 ORDER BY item0.timestamp DESC"

def fetch_and_extract(token, filters, start_ms, end_ms, limit, fields_arg):
    field_map = discover_fields(token)
    piql = build_piql(start_ms, end_ms, filters, field_map)
    sys.stderr.write(f"[*] Generated PIQL: {piql}\n")
    
    try:
        # --- FIX: Uses imported VRLI_HOST correctly now ---
        resp = requests.post(f"https://{VRLI_HOST}:9543/api/v2/queries", 
            headers={"Authorization":f"Bearer {token}", "Content-Type":"application/json"},
            json={"query": piql, "limit": limit, "timeout": 60000}, verify=False)
        
        data = resp.json()
        if "errorMessage" in data: return []

        events = []
        id_to_def = {v["id"]: v for k,v in field_map.items()} 

        for item in data.get("messageResults", {}).get("msgIds", []):
            content = item.get("msgContent", {})
            orig = content.get("originalText", "")
            row = { "timestamp": content.get("timestamp"), "datetime": datetime.datetime.fromtimestamp(content.get("timestamp")/1000).strftime('%Y-%m-%d %H:%M:%S'), "host": content.get("fields", {}).get("hostname", {}).get("value"), "message": orig }
            
            extracted = content.get("regexFields", []) + content.get("additionalExtractedFields", [])
            found_keys = set()
            for f in extracted:
                definition = id_to_def.get(f.get("name"))
                if definition:
                    row[definition["original_name"]] = f.get("content") or f.get("value")
                    found_keys.add(definition["original_name"])

            fields_to_check = [x.strip() for x in fields_arg.split(',')] if fields_arg else [k for k in KNOWN_DEFINITIONS if k not in found_keys]
            for fname in fields_to_check:
                if fname not in row or row[fname] is None:
                     finfo = field_map.get(fname)
                     if finfo and finfo.get("py_pattern"):
                         match = finfo["py_pattern"].search(orig)
                         if match:
                             try: row[fname] = match.group("val")
                             except: pass
            events.append(row)
        return events
    except Exception as e: sys.stderr.write(f"[-] Fetch Error: {e}\n"); return []
