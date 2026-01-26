import sys
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO
from datetime import datetime
import argparse

def get_remote_sar_data(hostname, flag):
    """
    Connects to 'hostname' via SSH and runs 'sar <flag>'.
    Returns a Pandas DataFrame.
    """
    try:
        # We use LC_ALL=C to ensure the date/number format is standard (English/24h)
        # ssh -q suppresses welcome banners/warnings that might break parsing
        ssh_cmd = [
            "ssh", "-q", 
            hostname, 
            f"LC_ALL=C sar {flag}"
        ]
        
        print(f"Connecting to {hostname}: Running 'sar {flag}'...")
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error running remote command on {hostname}.")
            print(f"Stderr: {result.stderr.strip()}")
            return None

        # Process output
        lines = result.stdout.split('\n')
        
        # Filter: Remove empty lines and Linux system header (first line usually)
        # We look for the line that starts with "Time" or "00:00:01" to identify the header
        cleaned_lines = []
        header_found = False
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            # Heuristic to find the start of data. 
            # Valid lines usually start with a timestamp (digit) or the word "Time" or "AM/PM"
            if "Time" in line or line.strip()[0].isdigit():
                header_found = True
            
            if header_found:
                cleaned_lines.append(line)

        if not cleaned_lines:
            print(f"No valid SAR data found for {flag} on {hostname}.")
            return None

        data_str = "\n".join(cleaned_lines)
        
        # Parse with Pandas
        df = pd.read_csv(StringIO(data_str), sep=r'\s+', engine='python')

        # Cleanup: Remove "Average:" rows
        if not df.empty and 'Average:' in df.iloc[:, 0].values:
            df = df[df.iloc[:, 0] != 'Average:']
        
        # Standardize Time Column
        # Sometimes the header is "Time" or "12:00:01", ensuring column 0 is named 'Time'
        df.rename(columns={df.columns[0]: 'Time'}, inplace=True)

        return df

    except Exception as e:
        print(f"Critical failure fetching data: {e}")
        return None

def plot_metrics(hostname):
    # 1. Fetch Data via SSH
    cpu_df = get_remote_sar_data(hostname, "-u")
    mem_df = get_remote_sar_data(hostname, "-r")
    load_df = get_remote_sar_data(hostname, "-q")

    if cpu_df is None or mem_df is None or load_df is None:
        print("❌ Aborting: Could not fetch all required datasets.")
        return

    print("Data fetched successfully. Generating plot...")

    # 2. Setup Plot
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15), sharex=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    fig.suptitle(f'Metrics for Host: {hostname} ({timestamp})', fontsize=16)

    # --- Plot 1: Load Average ---
    # Metrics: ldavg-1, ldavg-5, ldavg-15
    # Note: Column names vary slightly by sysstat version ("ldavg-1" vs "runq-sz" sometimes, but usually ldavg)
    if 'ldavg-1' in load_df.columns:
        ax1.plot(load_df['Time'], load_df['ldavg-1'], label='1-min Load', color='blue')
        ax1.plot(load_df['Time'], load_df['ldavg-5'], label='5-min Load', color='orange')
        ax1.plot(load_df['Time'], load_df['ldavg-15'], label='15-min Load', color='green')
    else:
        # Fallback if columns are different, plot first 3 numeric columns
        cols = load_df.columns[1:4]
        for col in cols:
            ax1.plot(load_df['Time'], load_df[col], label=col)

    ax1.set_title('Load Average')
    ax1.set_ylabel('Load')
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend()

    # --- Plot 2: CPU Utilization ---
    # Calculate Usage = 100 - %idle
    idle_col = '%idle' if '%idle' in cpu_df.columns else '%id'
    
    if idle_col in cpu_df.columns:
        # Ensure numeric
        cpu_usage = 100 - pd.to_numeric(cpu_df[idle_col], errors='coerce')
        ax2.plot(cpu_df['Time'], cpu_usage, label='Total CPU Usage (%)', color='red')
        ax2.fill_between(cpu_df['Time'], cpu_usage, color='red', alpha=0.1)
    
    ax2.set_title('CPU Utilization')
    ax2.set_ylabel('Usage (%)')
    ax2.set_ylim(0, 100)
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend()

    # --- Plot 3: Memory Utilization ---
    # Metric: %memused
    mem_col = '%memused' if '%memused' in mem_df.columns else '%mem'
    
    if mem_col in mem_df.columns:
        mem_data = pd.to_numeric(mem_df[mem_col], errors='coerce')
        ax3.plot(mem_df['Time'], mem_data, label='Memory Used (%)', color='purple')
        ax3.fill_between(mem_df['Time'], mem_data, color='purple', alpha=0.1)

    ax3.set_title('Memory Utilization')
    ax3.set_ylabel('Used (%)')
    ax3.set_xlabel('Time')
    ax3.set_ylim(0, 100)
    ax3.grid(True, linestyle='--', alpha=0.6)
    ax3.legend()

    # Formatting
    plt.xticks(rotation=45)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    # Save
    output_filename = f"sar_{hostname}_{timestamp}.png"
    plt.savefig(output_filename)
    print(f"✔ Graph saved: {output_filename}")

if __name__ == "__main__":
    # Argument Parsing
    parser = argparse.ArgumentParser(description="Plot SAR metrics from a remote host via SSH.")
    parser.add_argument("hostname", help="The remote hostname or IP address to connect to.")
    args = parser.parse_args()

    plot_metrics(args.hostname)
