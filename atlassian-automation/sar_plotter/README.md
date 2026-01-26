# SAR Plotter

## Overview

A framework for plotting and analyzing SAR (System Activity Reporter) data from Linux systems. This framework helps visualize system performance metrics over time, including CPU, memory, disk, and network utilization.

## What It Does

- **SAR Data Plotting**: Creates visualizations from SAR data files
- **Remote SAR Analysis**: Fetches and plots SAR data from remote servers
- **Historical Analysis**: Analyzes SAR history files for trend analysis
- **Performance Metrics**: Visualizes CPU, memory, disk, network, and other system metrics
- **Time Series Visualization**: Creates time series plots for performance analysis

## Prerequisites

- Python 3.7+
- Matplotlib library: `pip install matplotlib`
- Pandas library: `pip install pandas`
- SSH access to remote servers (for remote plotting)
- SAR data files or access to `/var/log/sa/` directory

## Configuration

### Script Configuration

Edit scripts to configure:

#### Remote Server Configuration (plot_remote_sar.py)
```python
SSH_USER = "your_user"
HOSTS = ["server1.example.com", "server2.example.com"]
SAR_DATA_PATH = "/var/log/sa"
```

**Configuration Parameters:**
- `SSH_USER`: SSH username for remote servers
- `HOSTS`: List of server hostnames
- `SAR_DATA_PATH`: Path to SAR data directory on remote servers

#### Local SAR Configuration (plot_sar_history.py)
```python
SAR_DATA_PATH = "/var/log/sa"
OUTPUT_DIR = "./plots"
```

**Configuration Parameters:**
- `SAR_DATA_PATH`: Local path to SAR data directory
- `OUTPUT_DIR`: Directory for output plots

### Server Names and Locations

- **Remote Servers**: Configured in `plot_remote_sar.py` as `HOSTS` array
- **SAR Data Path**: Configured as `SAR_DATA_PATH` (typically `/var/log/sa`)

### Thresholds

- **Time Range**: Configured via script parameters or date range selection
- **Metric Selection**: Choose which metrics to plot (CPU, memory, disk, etc.)

## How to Use

### 1. Setup

```bash
# Install dependencies
pip install matplotlib pandas

# Configure servers in plot_remote_sar.py (if using remote plotting)
# Or configure local path in plot_sar_history.py
```

### 2. Run Plotting

```bash
# Plot remote SAR data
python3 plot_remote_sar.py

# Plot local SAR history
python3 plot_sar_history.py

# With date range (if supported)
python3 plot_sar_history.py --start-date 2025-01-01 --end-date 2025-01-31
```

### 3. View Output

Generated plots are saved to the configured output directory (typically `./plots` or current directory).

## Credentials/Tokens

### SSH Credentials (for remote plotting)

- **SSH User**: Configured in scripts
- **SSH Key**: Use passwordless SSH (set up SSH keys)

### Security Notes

- **Never commit SSH keys to version control**
- Use passwordless SSH for automation
- SAR data may contain system information - handle appropriately

## Plot Types

The framework can generate plots for:

- **CPU Utilization**: CPU usage over time
- **Memory Usage**: Memory consumption patterns
- **Disk I/O**: Disk read/write operations
- **Network Traffic**: Network interface statistics
- **Load Average**: System load over time
- **Process Statistics**: Process-related metrics

## Troubleshooting

### Common Issues

1. **SAR Files Not Found**: Verify `SAR_DATA_PATH` is correct
2. **SSH Connection Failed**: Check SSH keys and server accessibility
3. **Permission Denied**: Ensure read access to SAR data files
4. **Missing Dependencies**: Install matplotlib and pandas

### Getting Help

- Review error messages in console output
- Verify SAR data files exist and are readable
- Check SSH connectivity for remote plotting

## Example Workflow

```bash
# 1. Configure servers
# Edit plot_remote_sar.py with your server hostnames

# 2. Install dependencies
pip install matplotlib pandas

# 3. Run remote plotting
python3 plot_remote_sar.py

# 4. Or plot local SAR history
python3 plot_sar_history.py

# 5. Review plots
# Check output directory for generated plots
```

## Files Overview

- `plot_remote_sar.py`: Plot SAR data from remote servers
- `plot_sar_history.py`: Plot local SAR history files

---

**Note**: This is production-ready code. Configure server hostnames and SAR data paths before execution.

