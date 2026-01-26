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

def get_session_token(username, password):
    auth_url = f"{BASE_URL}/sessions"
    try:
        resp = requests.post(
            auth_url, 
            json={"username": username, "password": password, "provider": PROVIDER}, 
            headers={"Content-Type": "application/json"}, 
            verify=False
        )
        return resp.json().get("sessionId")
    except Exception as e:
        sys.stderr.write(f"[-] Auth Error: {e}\n")
        return None

def fetch_poc_data(token, query, days, request_fields):
    current_time_ms = int(time.time() * 1000)
    start_time_ms = current_time_ms - (days * 24 * 3600 * 1000)
    
    # Base constraints
    constraints = [
        f"timestamp/GT {start_time_ms}",
        f"text/CONTAINS {urllib.parse.quote(query, safe='')}"
    ]
    
    url = f"{BASE_URL}/events/{'/'.join(constraints).replace(' ', '%20')}"
    
    # Add the specific fields parameter if requested (based on your finding)
    params = {"limit": 1000000} # Small limit for PoC
    if request_fields:
        params["fields"] = request_fields

    print(f"[*] Requesting URL: {url}")
    print(f"[*] Params: {params}")

    try:
        resp = requests.get(
            url, 
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, 
            params=params, 
            verify=False
        )
        data = resp.json()
        events = data.get("events", [])
        
        print(f"\n[*] API returned {len(events)} events.\n")
        
        results = []
        for e in events:
            # 1. Capture the Standard Message
            txt = e.get('text', '')
            ts = e.get('timestamp')
            
            # 2. Capture ALL Fields (The missing piece)
            # vRLI returns a list: [{'name': 'appname', 'content': 'jira'}, ...]
            # We convert this to a clean dictionary: {'appname': 'jira'}
            fields_map = {f['name']: f['content'] for f in e.get('fields', [])}
            
            # 3. Create the Enhanced Record
            enhanced_record = {
                "timestamp": ts,
                "message_preview": txt[:100], # Preview only for readability
                "all_extracted_fields": fields_map  # <--- THIS IS THE NEW DATA
            }
            results.append(enhanced_record)
            
        return results

    except Exception as e:
        sys.stderr.write(f"[-] API Error: {e}\n")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, help="Search term (e.g. 'error')")
    parser.add_argument("--request-fields", help="Optional: Comma-separated list of fields to request from API")
    parser.add_argument("--auth-user")
    parser.add_argument("--password")
    args = parser.parse_args()
    
    u = args.auth_user or os.environ.get("VRLI_USERNAME")
    p = args.password or os.environ.get("VRLI_PASSWORD")
    
    if u and p:
        token = get_session_token(u, p)
        if token: 
            data = fetch_poc_data(token, args.query, 1, args.request_fields)
            # Pretty print the JSON to seeing exactly what we got
            print(json.dumps(data, indent=4))
    else:
        print("[-] Credentials missing.")
