import sys
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import StringIO
from datetime import datetime, timedelta
import argparse

# --- Configuration ---
# RHEL/CentOS store logs in /var/log/sa/
# Debian/Ubuntu store logs in /var/log/sysstat/
# Since you are on RHEL 8, we default to the RHEL path.
REMOTE_LOG_DIR = "/var/log/sa"

def get_day_data(hostname, target_date, flag):
    """
    Fetches SAR data for a specific date from the remote host.
    Target_date: datetime object
    """
    # Construct filename based on day of month (e.g., sa17)
    day_str = target_date.strftime("%d")
    remote_file = f"{REMOTE_LOG_DIR}/sa{day_str}"
    
    # We use -f to read a specific file
    cmd_flag = f"{flag} -f {remote_file}"
    
    try:
        ssh_cmd = ["ssh", "-q", hostname, f"LC_ALL=C sar {cmd_flag}"]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # This is common (e.g., file doesn't exist for that day)
            return None

        lines = result.stdout.split('\n')
        cleaned_lines = []
        header_found = False
        
        for line in lines:
            if not line.strip(): continue
            # Find header (starts with Time or a digit)
            if "Time" in line or (line[0].isdigit() and ("AM" in line or "PM" in line or ":" in line)):
                header_found = True
            if header_found:
                cleaned_lines.append(line)

        if not cleaned_lines:
            return None

        data_str = "\n".join(cleaned_lines)
        df = pd.read_csv(StringIO(data_str), sep=r'\s+', engine='python')

        # Clean "Average" and "RESTART" lines
        if not df.empty:
            df = df[~df.iloc[:, 0].astype(str).str.contains('Average|RESTART|LINUX', case=False)]

        # Standardize Time Column
        df.rename(columns={df.columns[0]: 'Time'}, inplace=True)
        
        # --- Crucial Step: Convert Time string to Full Datetime ---
        # We must combine the 'target_date' (YYYY-MM-DD) with the 'Time' (HH:MM:SS) column
        # to place this data correctly on the 30-day timeline.
        
        # Helper to combine date + time string
        def parse_full_datetime(time_str):
            try:
                # Handle AM/PM if present
                fmt = "%H:%M:%S"
                if "AM" in time_str or "PM" in time_str:
                    fmt = "%I:%M:%S %p"
                
                t = datetime.strptime(time_str, fmt).time()
                return datetime.combine(target_date.date(), t)
            except:
                return None

        df['Datetime'] = df['Time'].apply(parse_full_datetime)
        df = df.dropna(subset=['Datetime']) # Drop rows where parsing failed
        
        return df

    except Exception:
        return None

def fetch_history(hostname, days, flag):
    print(f"Fetching {flag} data for the last {days} days...")
    all_dfs = []
    
    # Iterate backwards from today
    for i in range(days):
        target_date = datetime.now() - timedelta(days=i)
        print(f"   ... processing {target_date.strftime('%Y-%m-%d')}", end="\r")
        
        df = get_day_data(hostname, target_date, flag)
        if df is not None and not df.empty:
            all_dfs.append(df)
            
    print(f"   ... Done fetching {flag}.                    ")
    
    if not all_dfs:
        return None
    
    # Combine all days into one sorted DataFrame
    full_df = pd.concat(all_dfs)
    full_df.sort_values('Datetime', inplace=True)
    return full_df

def plot_metrics(hostname, days):
    # 1. Fetch History
    cpu_df = fetch_history(hostname, days, "-u")
    mem_df = fetch_history(hostname, days, "-r")
    load_df = fetch_history(hostname, days, "-q")

    if cpu_df is None and mem_df is None and load_df is None:
        print("No data found for the specified range. Is sysstat installed and logging?")
        return

    print("Generating plot...")

    # 2. Setup Plot
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    fig.suptitle(f'System Metrics: {hostname} (Last {days} Days)', fontsize=16)

    # Helper to handle missing data gracefully
    def safe_plot(ax, df, y_col, label, color, fill=False):
        if df is not None and y_col in df.columns:
            # Convert to numeric, forcing errors to NaN
            data = pd.to_numeric(df[y_col], errors='coerce')
            ax.plot(df['Datetime'], data, label=label, color=color, linewidth=1)
            if fill:
                ax.fill_between(df['Datetime'], data, color=color, alpha=0.1)

    # --- Plot 1: Load Average ---
    if load_df is not None:
        # Try to find load columns
        col_1 = 'ldavg-1' if 'ldavg-1' in load_df.columns else load_df.columns[1]
        col_5 = 'ldavg-5' if 'ldavg-5' in load_df.columns else load_df.columns[2]
        col_15 = 'ldavg-15' if 'ldavg-15' in load_df.columns else load_df.columns[3]
        
        safe_plot(ax1, load_df, col_1, '1-min Load', 'blue')
        safe_plot(ax1, load_df, col_5, '5-min Load', 'orange')
        safe_plot(ax1, load_df, col_15, '15-min Load', 'green')
    
    ax1.set_title('Load Average')
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend(loc='upper left')

    # --- Plot 2: CPU Utilization ---
    if cpu_df is not None:
        idle_col = '%idle' if '%idle' in cpu_df.columns else '%id'
        if idle_col in cpu_df.columns:
            cpu_usage = 100 - pd.to_numeric(cpu_df[idle_col], errors='coerce')
            # Add to DF for plotting
            cpu_df['calc_usage'] = cpu_usage
            safe_plot(ax2, cpu_df, 'calc_usage', 'Total CPU Usage (%)', 'red', fill=True)
    
    ax2.set_title('CPU Utilization')
    ax2.set_ylim(0, 100)
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend(loc='upper left')

    # --- Plot 3: Memory Utilization ---
    if mem_df is not None:
        mem_col = '%memused' if '%memused' in mem_df.columns else '%mem'
        safe_plot(ax3, mem_df, mem_col, 'Memory Used (%)', 'purple', fill=True)

    ax3.set_title('Memory Utilization')
    ax3.set_ylim(0, 100)
    ax3.grid(True, linestyle='--', alpha=0.6)
    ax3.legend(loc='upper left')

    # --- Formatting X-Axis for Dates ---
    # Since we have many days, we format as "Mon DD"
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax3.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days//10))) # Show ~10 ticks max
    plt.xticks(rotation=45)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    output_filename = f"sar_history_{hostname}_{timestamp}.png"
    plt.savefig(output_filename)
    print(f"✔ Success! Graph saved: {output_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot SAR history from remote host.")
    parser.add_argument("hostname", help="Remote hostname")
    # Default to 30 days if not provided
    parser.add_argument("days", nargs='?', type=int, default=30, help="Number of days to plot (default: 30)")
    
    args = parser.parse_args()
    
    plot_metrics(args.hostname, args.days)
