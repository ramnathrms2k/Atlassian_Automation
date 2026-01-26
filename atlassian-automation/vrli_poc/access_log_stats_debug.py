import json
import re
import sys
import argparse
from collections import defaultdict

HUMAN_USER_REGEX = re.compile(r'^[a-zA-Z]{2}\d{6}$')

def parse_jira_debug(line):
    try:
        # DEBUG: Print the line being parsed
        # print(f"DEBUG LINE: {line[:50]}...") 

        parts = line.split('[', 1)
        if len(parts) < 2: 
            return None, "Missing Date Bracket '['"
        
        meta = parts[0].strip().split()
        # We expect at least: IP, Session, User (3 parts) OR IP, User (2 parts)
        if len(meta) < 2: 
            return None, f"Not enough metadata columns: {meta}"
        
        user = meta[-1] # Last item before date is usually User
        
        # Split by quotes to find request
        q_split = line.split('"')
        if len(q_split) < 3: 
            return None, "Missing quoted Request string"
        
        # Duration is in the part AFTER the request
        post_req = q_split[-1].strip().split()
        if not post_req:
             return None, "No data after Request string"
        
        # Try finding the duration (usually the largest/last number)
        # Standard: Status, Bytes, Duration
        # We'll try the last item first
        dur_cand = post_req[-1]
        if not dur_cand.isdigit():
             # Try 3rd column if last is not digit (sometimes there's a "-")
             if len(post_req) >= 3 and post_req[2].isdigit():
                 dur_cand = post_req[2]
             else:
                 return None, f"Could not find numeric duration in: {post_req}"

        return {
            "time": "0", 
            "user": user, 
            "duration": int(dur_cand)
        }, "OK"
        
    except Exception as e:
        return None, f"Crash: {e}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    try:
        with open(args.file, 'r') as f:
            data = json.load(f)
    except:
        print("[-] Error: Could not read JSON file.")
        sys.exit(1)

    print(f"[*] Analyzing {len(data)} raw events...")
    
    success = 0
    failures = 0
    human_skips = 0

    print("\n--- DIAGNOSTIC LOG (First 5 Failures) ---")
    
    for i, event in enumerate(data):
        line = event.get('message', '')
        if not line: continue
        
        parsed, reason = parse_jira_debug(line)
        
        if not parsed:
            failures += 1
            if failures <= 5:
                print(f"FAIL #{failures}: {reason}")
                print(f"   LINE: {line}")
            continue
            
        # Check Human Logic
        if not HUMAN_USER_REGEX.match(parsed['user']):
            human_skips += 1
            if human_skips <= 5:
                 print(f"SKIP (Not Human): User='{parsed['user']}'")
            continue

        success += 1

    print("-" * 60)
    print(f"TOTAL PROCESSED: {len(data)}")
    print(f"PARSE FAILURES:  {failures}")
    print(f"NON-HUMAN SKIPS: {human_skips}")
    print(f"SUCCESSFUL HITS: {success}")
    
    if success == 0:
        print("\n[!] CONCLUSION: The script works, but your filter rejected everything.")
        print("    Likely cause: The 100 events fetched were all bots/healthchecks.")

if __name__ == "__main__":
    main()
