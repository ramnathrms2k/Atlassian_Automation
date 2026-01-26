# Jira Response Time Tracker

## Overview

A Flask-based web interface for monitoring slow requests from Jira access logs across multiple Jira Data Center servers. This framework analyzes access logs in real-time to identify requests taking longer than a configurable threshold, grouped by user ID, with statistics on count, maximum time, last time, and timestamps.

## What It Does

- **Access Log Analysis**: Analyzes Jira access logs from multiple servers to identify slow requests
- **User-Based Statistics**: Groups slow requests by User ID and provides:
  - Count of slow requests per user
  - Maximum time taken for any request
  - Last time taken for the most recent slow request
  - Last timestamp of slow request
- **Multi-Server Monitoring**: Displays statistics from multiple Jira servers in separate scrollable boxes
- **Real-Time Updates**: On-demand refresh to get latest statistics
- **Configurable Thresholds**: Set custom threshold for what constitutes a "slow" request
- **Scrollable Tables**: Tables with scroll bars for handling large datasets
- **JSON API**: RESTful API endpoint for programmatic access

## Prerequisites

- Python 3.7+
- Flask: `pip install -r requirements.txt`
- Passwordless SSH access from your machine to all Jira servers
- Access to Jira access log files on the servers
- Network access to Jira servers

## Configuration

### Main Configuration File: `config.py`

Edit `config.py` to configure your environment:

#### Jira Server Configuration
```python
JIRA_SERVERS = [
    {
        "name": "Jira Server 1 (Prod A)",
        "hostname": "jira-server-1.example.com",
        "log_path": "/export/jira/logs"
    },
    {
        "name": "Jira Server 2 (Prod B)",
        "hostname": "jira-server-2.example.com",
        "log_path": "/export/jira/logs"
    },
    {
        "name": "Jira Server 3 (Prod C)",
        "hostname": "jira-server-3.example.com",
        "log_path": "/export/jira/logs"
    },
]
```

**Configuration Parameters:**
- `name`: Display name for the server in the dashboard
- `hostname`: Server hostname for SSH access (must match actual server hostname)
- `log_path`: Path to the directory containing access logs on the server

#### SSH Configuration
```python
SSH_USER = "your_ssh_user"  # Replace with your SSH username
SSH_TIMEOUT = 10  # seconds
```

**Configuration Parameters:**
- `SSH_USER`: **Replace with your SSH username** (must have passwordless SSH configured)
- `SSH_TIMEOUT`: SSH connection timeout in seconds

#### Access Log Configuration
```python
ACCESS_LOG_FORMAT = "access_log.%Y-%m-%d"  # Format for today's log file
```

**Configuration Parameters:**
- `ACCESS_LOG_FORMAT`: strftime format string for the log file name
  - Example: `"access_log.%Y-%m-%d"` produces `"access_log.2026-01-21"` for January 21, 2026
  - Adjust based on your log file naming convention

#### Analysis Configuration
```python
TAIL_LINES = 5000  # Number of lines to tail from the access log
THRESHOLD_MS = 60000  # Threshold in milliseconds (requests taking longer than this will be tracked)
REFRESH_INTERVAL = 5  # Refresh interval in seconds (for reference, not currently used for auto-refresh)
```

**Configuration Parameters:**
- `TAIL_LINES`: Number of lines to analyze from the end of the access log file
- `THRESHOLD_MS`: **Threshold in milliseconds** - requests taking longer than this will be tracked
  - Default: 60000ms (60 seconds)
  - Adjust based on your performance requirements
- `REFRESH_INTERVAL`: Refresh interval in seconds (currently informational, manual refresh only)

## How to Use

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure settings in config.py
# - Replace "your_ssh_user" with actual SSH username
# - Update server hostnames and log paths
# - Adjust threshold, tail lines, and log format as needed
```

### 2. Configure Passwordless SSH

Ensure passwordless SSH is configured from your machine to all Jira servers:

```bash
# Generate SSH key (if not already done)
ssh-keygen -t rsa -b 4096

# Copy key to each server
ssh-copy-id your_ssh_user@jira-server-1.example.com
ssh-copy-id your_ssh_user@jira-server-2.example.com
ssh-copy-id your_ssh_user@jira-server-3.example.com

# Test connection
ssh your_ssh_user@jira-server-1.example.com "echo 'Connection successful'"
```

### 3. Verify Access Log Format

The framework assumes the following access log format:
- Field `$3` = User ID
- Field `$4` = Timestamp (with brackets)
- Field `$10` = Time taken in milliseconds

If your log format differs, you may need to adjust the awk command in `app.py`.

### 4. Run the Application

```bash
# Start the Flask application
python3 app.py
```

The dashboard will be available at:
```
http://localhost:5002
```

### 5. Using the Dashboard

1. **Click "Refresh Data"** to fetch response time statistics from all servers
2. **View Statistics**: Each server displays in its own box with:
   - Server status (Online/Error)
   - Number of records found
   - Scrollable table with statistics
3. **Scroll Tables**: If the list is long, use the scroll bars to view all entries
4. **Refresh Again**: Click "Refresh Data" again to get updated statistics

## Dashboard Features

### Server Boxes
- **Three separate boxes** - One for each configured server
- **Scrollable tables** - Tables have scroll bars for long lists
- **Status indicators** - Shows Online/Error status for each server
- **Record counts** - Displays total number of slow requests found

### Statistics Table
Each table shows:
- **Count**: Number of slow requests for this user
- **Max Time (ms)**: Maximum time taken for any request by this user
- **Last Time (ms)**: Time taken for the most recent slow request
- **Last Timestamp**: Timestamp of the most recent slow request
- **User ID**: User ID from the access log

### Error Handling
- **Connection Errors**: Shows error message if SSH connection fails
- **File Not Found**: Shows error if log file doesn't exist
- **No Data**: Shows message if no slow requests found (all requests below threshold)

## Access Log Format

The framework expects access logs in a standard format where:
- **Field 3** (`$3`): User ID
- **Field 4** (`$4`): Timestamp (with brackets, e.g., `[21/Jan/2026:13:00:00 -0800]`)
- **Field 10** (`$10`): Time taken in milliseconds

If your access log format differs, you'll need to adjust the awk command in the `get_response_time_stats()` function in `app.py`.

## API Endpoints

- **`/`**: Main dashboard page
- **`/refresh`**: Manual refresh endpoint (triggers data fetch and displays results)
- **`/api/stats`**: JSON API endpoint for programmatic access

### Example API Response
```json
{
  "servers": [
    {
      "server_name": "Jira Server 1 (Prod A)",
      "hostname": "jira-server-1.example.com",
      "status": "Online",
      "error": null,
      "data": [
        {
          "count": 15,
          "max_time_taken": 125000,
          "last_time_taken": 95000,
          "last_timestamp": "21/Jan/2026:13:45:00 -0800",
          "user_id": "user123"
        }
      ],
      "total_records": 1
    }
  ],
  "last_update": "2026-01-21 13:50:00",
  "config": {
    "threshold_ms": 60000,
    "tail_lines": 5000,
    "log_format": "access_log.%Y-%m-%d"
  }
}
```

## Troubleshooting

### SSH Connection Issues
```bash
# Test SSH connection
ssh your_ssh_user@jira-server-1.example.com "echo 'Connection successful'"

# Verify SSH key is in authorized_keys
ssh your_ssh_user@jira-server-1.example.com "cat ~/.ssh/authorized_keys"
```

### Log File Not Found
- Verify the log path in `config.py` matches the actual path on the server
- Check that the log file exists: `ssh user@server "ls -la /export/jira/logs/access_log.2026-01-21"`
- Verify the `ACCESS_LOG_FORMAT` matches your log file naming convention

### No Data Returned
- Check that there are actually slow requests in the last N lines
- Verify the threshold is appropriate (try lowering it to see if data appears)
- Check the log file has recent entries: `ssh user@server "tail -n 100 /export/jira/logs/access_log.2026-01-21"`

### Wrong Data Format
- Verify your access log format matches the expected format
- Check field positions (User ID should be field 3, Time taken should be field 10)
- Adjust the awk command in `app.py` if your format differs

### Performance Issues
- Reduce `TAIL_LINES` if analysis is slow
- Increase `SSH_TIMEOUT` if connections are timing out
- Check network connectivity to servers

## Security Notes

- **SSH Keys**: Use passwordless SSH with key-based authentication
- **Log Access**: Ensure SSH user has read access to log files
- **Network**: Ensure dashboard server has network access to Jira servers
- **Credentials**: SSH username is stored in `config.py` (no passwords needed with key-based auth)

## Logging

Logs are written to:
- **File**: `jira_response_time_tracker.log` (in the framework directory)
- **Console**: Standard output

Log levels:
- **INFO**: General operations, data fetch start/end
- **WARNING**: Failed operations, parsing errors
- **ERROR**: Connection failures, critical errors
- **DEBUG**: Detailed command execution (if enabled)

## Future Enhancements

- Auto-refresh functionality with configurable intervals
- Historical trending and charts
- Export functionality (CSV, PDF reports)
- Alert notifications (email, Slack) for high counts
- Filtering and sorting options in the UI
- Additional statistics (average time, percentile analysis)
- Support for multiple log files (historical analysis)

## Support

For issues or questions:
1. Check logs: `jira_response_time_tracker.log`
2. Verify configuration in `config.py`
3. Test SSH connections manually
4. Verify log file format and accessibility
5. Review error messages in dashboard UI
