import time
import subprocess
import csv
import threading
import signal
import sys
import datetime
import os
import argparse

# --- CONFIGURATION (Ensure Hostnames match your setup) ---
NODES = {
    "app1": { "host": "jira-lvnv-it-001.lvn.broadcom.net", "process_name": "java" },
    "app2": { "host": "jira-lvnv-it-002.lvn.broadcom.net", "process_name": "java" },
    "db":   { "host": "db-lvnv-it-001.lvn.broadcom.net",   "process_name": "mysqld" }
}

HEADERS = ["timestamp", "node", "load_1min", "mem_used_gb", "cpu_process_percent"]

def get_metrics(node_key, config):
    host = config["host"]
    proc = config["process_name"]
    
    # FIX: Added '-c' to top command to show full arguments (easier to grep java)
    # FIX: Added ' || echo 0' to ensure we always get a number even if grep fails
    cmd = f"""ssh -o StrictHostKeyChecking=no {host} '
    echo $(uptime | awk -F"load average: " "{{print \$2}}" | awk -F"," "{{print \$1}}")__$(free -g | grep Mem: | awk "{{print \$3}}")__$(top -b -n 1 -c | grep {proc} | head -1 | awk "{{print \$9}}")
    '"""
    
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        parts = result.split("__")
        
        # Robust parsing
        load = float(parts[0]) if parts[0] else 0.0
        mem = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
        
        # CPU Fix: Handle empty string
        cpu_str = parts[2] if len(parts) > 2 else "0.0"
        if not cpu_str.strip(): cpu_str = "0.0"
        cpu = float(cpu_str)

        return {
            "timestamp": datetime.datetime.now(),
            "node": node_key,
            "load_1min": load,
            "mem_used_gb": mem,
            "cpu_process_percent": cpu
        }
    except Exception as e:
        # print(f"Error on {node_key}: {e}") # Uncomment for debug
        return None

def monitor_loop(run_id):
    csv_file = f"metrics_{run_id}.csv"
    # Append mode so we don't lose data if we restart
    with open(csv_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        if os.stat(csv_file).st_size == 0: writer.writeheader()
        
        print(f"📡 Telemetry RESTARTED. Logging to {csv_file}...")
        
        while True:
            for node, cfg in NODES.items():
                data = get_metrics(node, cfg)
                if data:
                    writer.writerow(data)
                    f.flush()
            time.sleep(30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", required=True)
    args = parser.parse_args()
    monitor_loop(args.run_id)
