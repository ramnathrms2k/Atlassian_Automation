import requests
import urllib3
import urllib.parse
import time
import argparse
import os
import json
import sys
import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VRLI_HOST = "lvn-rnd-unix-logs.lvn.broadcom.net" 
BASE_URL = f"https://{VRLI_HOST}:9543/api/v2"
PROVIDER = "ActiveDirectory"
API_BATCH_SIZE = 2500

def get_session_token(username, password):
    auth_url = f"{BASE_URL}/sessions"
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(
            auth_url, 
            json={"username": username, "password": password, "provider": PROVIDER}, 
            headers=headers, 
            verify=False
        )
        return resp.json().get("sessionId")
    except Exception as e: 
        sys.stderr.write(f"[-] Auth Error: {e}\n")
        return None

def fetch_until_satisfied(token, primary_query, host_filter, file_filter, include_list, days, target_count):
    current_time_ms = int(time.time() * 1000)
    start_time_ms = current_time_ms - (days * 24 * 3600 * 1000)
    search_window_end = current_time_ms 
    collected_events = []
    
    sys.stderr.write(f"[*] Goal: Collect {target_count} relevant events.\n")

    while len(collected_events) < target_count:
        constraints = [
            f"timestamp/GT {start_time_ms}",
            f"timestamp/LT {search_window_end}",
            f"text/CONTAINS {urllib.parse.quote(primary_query, safe='')}"
        ]
        url = f"{BASE_URL}/events/{'/'.join(constraints).replace(' ', '%20')}"
        
        try:
            resp = requests.get(
                url, 
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, 
                params={"limit": API_BATCH_SIZE}, 
                verify=False
            )
            data = resp.json()
            events = data.get("events", [])
            if not events: break
                
            batch_matches = []
            oldest_in_batch = search_window_end 
            
            for e in events:
                ts = e.get('timestamp')
                if ts < oldest_in_batch: oldest_in_batch = ts
                
                txt = e.get('text', '')
                
                # --- NEW: Capture All Extracted Fields ---
                # vRLI sends fields as a list of dicts: [{'name': 'appname', 'content': 'jira'}]
                # We flatten this to: {'appname': 'jira'}
                fields_map = {f['name']: f['content'] for f in e.get('fields', [])}
                
                # Extract core fields for filtering
                host = fields_map.get('hostname', e.get('source', 'Unknown-Host'))
                fpath = fields_map.get('filepath', '')

                if host_filter and host_filter not in host: continue
                if file_filter and file_filter not in fpath: continue
                if include_list and not all(term in txt for term in include_list): continue

                batch_matches.append({
                    "timestamp": ts, 
                    "message": txt, 
                    "host": host,
                    "extracted_fields": fields_map  # Saving the rich data!
                })

            needed = target_count - len(collected_events)
            if len(batch_matches) > needed:
                collected_events.extend(batch_matches[:needed])
            else:
                collected_events.extend(batch_matches)
            
            sys.stderr.write(f"    Batch: scanned {len(events)} raw -> kept {len(batch_matches)} valid. Total: {len(collected_events)}/{target_count}\n")
            
            if oldest_in_batch >= search_window_end: break
            search_window_end = oldest_in_batch - 1

        except Exception as e:
            sys.stderr.write(f"[-] API Error: {e}\n")
            break
            
    if collected_events:
        latest = datetime.datetime.fromtimestamp(collected_events[0]['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S')
        earliest = datetime.datetime.fromtimestamp(collected_events[-1]['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S')
        sys.stderr.write(f"[*] Analysis Timeframe: {earliest} to {latest}\n")

    return collected_events

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--host"); parser.add_argument("--file")
    parser.add_argument("--include", action='append')
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--auth-user"); parser.add_argument("--password")
    args = parser.parse_args()
    
    u = args.auth_user or os.environ.get("VRLI_USERNAME")
    p = args.password or os.environ.get("VRLI_PASSWORD")
    
    if u and p:
        token = get_session_token(u, p)
        if token: 
            results = fetch_until_satisfied(
                token, args.query, args.host, args.file, 
                args.include, args.days, args.limit
            )
            print(json.dumps(results, indent=2))
