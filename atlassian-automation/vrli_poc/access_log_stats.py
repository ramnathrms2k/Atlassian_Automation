import json
import re
import sys
import argparse
import math
from collections import defaultdict

# --- CONFIGURATION ---
HUMAN_USER_REGEX = re.compile(r'^[a-zA-Z]{2}\d{6}$')

# --- PARSERS ---
def parse_confluence(line):
    # Format: [Date] User Thread IP Method URL Protocol Status Duration(ms) ...
    # We specifically look for the Method + URL pattern to be robust
    try:
        # Extract basic parts
        match = re.search(r'^\[(.*?)\]\s+(\S+)\s+.*?\s+(\d+)ms', line)
        if not match: return None
        
        timestamp = match.group(1)
        user = match.group(2)
        duration = int(match.group(3))
        
        # Extract URL: Look for "GET /path" or "POST /path"
        # Simple split approach for the middle section
        # The URL is usually after the IP address
        url = "Unknown"
        # Find standard HTTP methods
        method_match = re.search(r'(GET|POST|PUT|DELETE|HEAD)\s+(\S+)', line)
        if method_match:
            url = method_match.group(2)
            # Clean URL: Remove query params for better grouping (optional)
            if '?' in url: url = url.split('?')[0]

        return {
            "time": timestamp, 
            "user": user, 
            "duration": duration,
            "url": url
        }
    except: return None

def parse_jira(line):
    # Format: 10.x.x.x ... User [Date] "GET /url HTTP/1.1" Status Bytes Duration
    try:
        pre = line.split('[', 1)
        if len(pre) < 2: return None
        
        user = pre[0].strip().split()[-1]
        ts = pre[1].split(']')[0]
        
        q_parts = line.split('"')
        if len(q_parts) < 3: return None
        
        # Request is q_parts[1]: "GET /rest/api/2/issue/123 HTTP/1.1"
        req_tokens = q_parts[1].split()
        url = "Unknown"
        if len(req_tokens) > 1:
            url = req_tokens[1]
            # Clean URL: Remove query params
            if '?' in url: url = url.split('?')[0]

        metrics = q_parts[2].strip().split()
        if len(metrics) < 3: return None
        dur = metrics[2]
        
        if not dur.isdigit(): return None
        return {
            "time": ts, 
            "user": user, 
            "duration": int(dur),
            "url": url
        }
    except: return None

# --- STATISTICS ENGINE ---
def get_percentile(data, p):
    if not data: return 0
    k = (len(data)-1) * (p/100.0)
    f = math.floor(k); c = math.ceil(k)
    if f == c: return data[int(k)]
    return data[int(f)] * (c-k) + data[int(c)] * (k-f)

def print_analysis_block(title, durations, T):
    count = len(durations)
    if count == 0: return

    buckets = {"0-1s": 0, "1-5s": 0, "5-10s": 0, "10-30s": 0, "30-60s": 0, ">60s": 0}
    sat, tol, frust = 0, 0, 0
    
    for d in durations:
        if d < 1000: buckets["0-1s"]+=1
        elif d < 5000: buckets["1-5s"]+=1
        elif d < 10000: buckets["5-10s"]+=1
        elif d < 30000: buckets["10-30s"]+=1
        elif d < 60000: buckets["30-60s"]+=1
        else: buckets[">60s"]+=1
        
        if d <= T: sat += 1
        elif d <= 4*T: tol += 1
        else: frust += 1

    apdex = (sat + (tol/2)) / count
    avg = sum(durations) / count
    
    print(f"\n>>> {title} (Sample: {count} requests)")
    print("-" * 65)
    print(f"{'Time Bucket':<12} | {'Count':<6} | {'%':<6} || {'Metric':<15} | {'Value'}")
    print("="*65)
    row_fmt = "{:<12} | {:<6} | {:<6} || {:<15} | {}"
    
    print(row_fmt.format("0-1s", buckets['0-1s'], f"{(buckets['0-1s']/count)*100:.1f}%", "Apdex Score", f"{apdex:.2f}"))
    print(row_fmt.format("1-5s", buckets['1-5s'], f"{(buckets['1-5s']/count)*100:.1f}%", "Average", f"{avg:.0f} ms"))
    print(row_fmt.format("5-10s", buckets['5-10s'], f"{(buckets['5-10s']/count)*100:.1f}%", "99th %", f"{get_percentile(durations, 99):.0f} ms"))
    print(row_fmt.format("10-30s", buckets['10-30s'], f"{(buckets['10-30s']/count)*100:.1f}%", "98th %", f"{get_percentile(durations, 98):.0f} ms"))
    print(row_fmt.format("30-60s", buckets['30-60s'], f"{(buckets['30-60s']/count)*100:.1f}%", "95th %", f"{get_percentile(durations, 95):.0f} ms"))
    print(row_fmt.format(">60s", buckets['>60s'], f"{(buckets['>60s']/count)*100:.1f}%", "90th %", f"{get_percentile(durations, 90):.0f} ms"))
    print(row_fmt.format("", "", "", "80th %", f"{get_percentile(durations, 80):.0f} ms"))
    print(row_fmt.format("", "", "", "Max Time", f"{durations[-1]} ms"))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True); parser.add_argument("--app", required=True)
    parser.add_argument("--type", required=True); parser.add_argument("--include", action='append')
    parser.add_argument("--threshold", type=int, default=1000)
    args = parser.parse_args()

    try:
        with open(args.file, 'r') as f:
            events = json.load(f)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    all_durations = []
    node_durations = defaultdict(list)
    url_stats = defaultdict(list) # Store durations per URL
    slow_users = defaultdict(lambda: {"count": 0, "max": 0, "last": None, "host": ""})

    for e in events:
        line = e.get('message', '')
        host = e.get('host', 'Unknown-Host') 
        
        if args.include and not all(term in line for term in args.include): continue

        parsed = parse_confluence(line) if args.app == 'confluence' else parse_jira(line)
        if not parsed: continue
        
        is_human = bool(HUMAN_USER_REGEX.match(parsed['user']))
        if args.type == 'human' and (not is_human or parsed['user'] == '-'): continue
        if args.type == 'service' and is_human: continue
        
        d = parsed['duration']
        all_durations.append(d)
        node_durations[host].append(d)
        url_stats[parsed['url']].append(d)
        
        if d > (args.threshold * 4):
            u = parsed['user']
            slow_users[u]["count"] += 1
            if d > slow_users[u]["max"]: 
                slow_users[u]["max"] = d
                slow_users[u]["host"] = host
            slow_users[u]["last"] = parsed['time']

    if not all_durations:
        print("No matching requests found."); sys.exit(0)

    all_durations.sort()
    
    # 1. OVERALL SUMMARY
    print("="*65)
    print(f"  PERFORMANCE REPORT: {args.app.upper()} ({args.type.upper()})")
    print("="*65)
    print_analysis_block("OVERALL SYSTEM", all_durations, args.threshold)

    # 2. TOP 5 URIs
    print("\n" + "="*65)
    print("  TOP 5 URIs BY VOLUME")
    print("="*65)
    print(f"{'Count':<6} | {'Avg(ms)':<7} | {'99th%':<7} | {'URI':<40}")
    print("-" * 65)
    
    # Sort by Count (Frequency) descending
    sorted_urls = sorted(url_stats.items(), key=lambda x: len(x[1]), reverse=True)
    
    for url, durs in sorted_urls[:5]:
        durs.sort()
        cnt = len(durs)
        avg = sum(durs) / cnt
        p99 = get_percentile(durs, 99)
        # Truncate URL for display
        disp_url = (url[:37] + '..') if len(url) > 39 else url
        print(f"{cnt:<6} | {avg:<7.0f} | {p99:<7.0f} | {disp_url}")


    # 3. CLUSTER BREAKDOWN
    print("\n" + "="*65); print("  CLUSTER NODE BREAKDOWN"); print("="*65)
    for node in sorted(node_durations.keys()):
        durs = sorted(node_durations[node])
        print_analysis_block(f"NODE: {node}", durs, args.threshold)

    # 4. FRUSTRATED USERS
    if slow_users:
        print("\n" + "="*65); print(f"  FRUSTRATED USERS (> {args.threshold * 4}ms)"); print("="*65)
        print(f"{'UserID':<15} | {'Count':<5} | {'Max(ms)':<9} | {'Node (Max)':<20} | {'Last Seen'}")
        print("-" * 75)
        sorted_slow = sorted(slow_users.items(), key=lambda x: x[1]['max'], reverse=True)
        for user, stats in sorted_slow[:20]:
            h_short = (stats['host'][:18] + '..') if len(stats['host']) > 20 else stats['host']
            print(f"{user:<15} | {stats['count']:<5} | {stats['max']:<9} | {h_short:<20} | {stats['last']}")

if __name__ == "__main__": main()
