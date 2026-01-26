import time
import subprocess
import csv
import threading
import signal
import sys
import matplotlib.pyplot as plt
import pandas as pd
import datetime
import os
import argparse

# --- INFRASTRUCTURE MAP ---
NODES = {
    "app1": { "host": "jira-lvnv-it-001.lvn.broadcom.net", "process_name": "java" },
    "app2": { "host": "jira-lvnv-it-002.lvn.broadcom.net", "process_name": "java" },
    "db":   { "host": "db-lvnv-it-001.lvn.broadcom.net",   "process_name": "mysqld" }
}

HEADERS = ["timestamp", "node", "load_1min", "mem_used_gb", "cpu_process_percent"]

def get_metrics(node_key, config):
    host = config["host"]
    proc = config["process_name"]
    
    # Robust SSH Command: 
    # 1. '-o StrictHostKeyChecking=no' avoids prompt hangs.
    # 2. 'top -b -n 1 -c' ensures full process names are visible for grep.
    cmd = f"""ssh -o StrictHostKeyChecking=no {host} '
    echo $(uptime | awk -F"load average: " "{{print \$2}}" | awk -F"," "{{print \$1}}")__$(free -g | grep Mem: | awk "{{print \$3}}")__$(top -b -n 1 -c | grep {proc} | head -1 | awk "{{print \$9}}")
    '"""
    
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        parts = result.split("__")
        
        # Safe Parsing: Handle empty or partial returns without crashing
        load = float(parts[0]) if parts[0] else 0.0
        mem = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
        
        # CPU Fix: Handle empty string if grep returns nothing
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
    except Exception:
        return None 

def monitor_loop(run_id, interval):
    csv_file = f"metrics_{run_id}.csv"
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        if not file_exists: writer.writeheader()
        
        print(f"📡 Telemetry active. Logging to {csv_file}...")
        while not stop_event.is_set():
            for node, cfg in NODES.items():
                data = get_metrics(node, cfg)
                if data:
                    writer.writerow(data)
                    f.flush()
            time.sleep(interval)

def generate_plots(run_id):
    csv_file = f"metrics_{run_id}.csv"
    if not os.path.exists(csv_file): return

    try:
        df = pd.read_csv(csv_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Generate 3 Plots
        for metric, label in [('load_1min', 'Load Avg'), ('mem_used_gb', 'Mem GB'), ('cpu_process_percent', 'CPU %')]:
            plt.figure(figsize=(10, 6))
            for node in df['node'].unique():
                plt.plot(df[df['node']==node]['timestamp'], df[df['node']==node][metric], label=node)
            plt.title(f"{label} ({run_id})"); plt.legend(); plt.grid(True); 
            plt.savefig(f"plot_{metric.split('_')[0]}_{run_id}.png")
            
        print(f"✅ Graphs generated for Run {run_id}")
    except Exception as e:
        print(f"❌ Graph generation failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--action", choices=["start", "plot"], required=True)
    args = parser.parse_args()

    if args.action == "start":
        stop_event = threading.Event()
        def signal_handler(sig, frame): stop_event.set(); sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler); signal.signal(signal.SIGTERM, signal_handler)
        monitor_loop(args.run_id, interval=30)
    elif args.action == "plot":
        generate_plots(args.run_id)
