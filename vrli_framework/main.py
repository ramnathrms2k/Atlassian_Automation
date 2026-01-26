# main.py
import argparse
import os
import sys
import getpass
import csv
import json
import datetime
from auth import get_token
from engine import fetch_and_extract

def parse_time(t_str):
    try: return int(datetime.datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
    except: sys.exit("[-] Invalid time format")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="vRLI Hybrid Framework")
    parser.add_argument("--filter", action='append', required=True)
    parser.add_argument("--fields")
    parser.add_argument("--format", choices=['csv', 'json'], default='csv')
    parser.add_argument("--hours", type=int, default=2)
    parser.add_argument("--minutes", type=int)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output")
    parser.add_argument("--auth-user")
    parser.add_argument("--password")
    
    args = parser.parse_args()
    
    if args.start:
        start_ms = parse_time(args.start)
        end_ms = parse_time(args.end) if args.end else int(datetime.datetime.now().timestamp() * 1000)
    elif args.minutes:
        end_ms = int(datetime.datetime.now().timestamp() * 1000)
        start_ms = end_ms - (args.minutes * 60 * 1000)
    else:
        end_ms = int(datetime.datetime.now().timestamp() * 1000)
        start_ms = end_ms - (args.hours * 3600 * 1000)

    u = args.auth_user or os.environ.get("VRLI_USERNAME") or input("User: ")
    p = args.password or os.environ.get("VRLI_PASSWORD") or getpass.getpass("Pass: ")
    
    if u and p:
        t = get_token(u, p)
        if t:
            data = fetch_and_extract(t, args.filter, start_ms, end_ms, args.limit, args.fields)
            
            if args.fields:
                wanted = [x.strip() for x in args.fields.split(',')]
                data = [{k: row.get(k, None) for k in wanted} for row in data]
                keys = wanted
            else:
                keys = ['timestamp','datetime','host','message']
                if data: keys += [k for k in set().union(*(d.keys() for d in data)) if k not in keys]

            if data:
                f = open(args.output, 'w', newline='', encoding='utf-8') if args.output else sys.stdout
                try:
                    if args.format == 'csv':
                        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                        w.writeheader()
                        w.writerows(data)
                    elif args.format == 'json':
                        json.dump(data, f, indent=2, default=str)
                finally:
                    if args.output: f.close()
            else:
                print("[-] No results.")
