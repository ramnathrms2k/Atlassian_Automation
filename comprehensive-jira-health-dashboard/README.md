# Comprehensive Jira Health Dashboard

## Overview

A comprehensive real-time health monitoring dashboard for Atlassian Jira Data Center clusters. This framework provides a web-based interface to monitor Jira index health, system metrics (CPU, memory, swap, load, disk usage), database connections, and database server metrics across all nodes in a Jira cluster.

## What It Does

- **Jira Index Health Monitoring**: Tracks database count, index count, archive count, and last update timestamps for each Jira server
- **System Metrics Collection**: Real-time monitoring of CPU, memory, swap, load average, and disk usage across all app nodes and database server
- **Dual Disk Usage Tracking**: 
  - App nodes: Local disk usage (`/export`) and shared home disk usage (from `cluster.properties`)
  - DB node: Local disk usage (`/export`) and binlogs disk usage (`/mysqllogs`)
- **Database Connection Monitoring**: Tracks active database connections per app node and total connections on the database server
- **Database Metrics**: Monitors total connections, connection utilization, active queries, and slow queries
- **Auto-Refresh**: Configurable automatic refresh with monitoring mode and on-demand refresh options
- **Color-Coded Alerts**: Visual indicators (green/yellow/red) based on configurable thresholds
- **JSON API**: RESTful API endpoint for programmatic access to health data

## Prerequisites

- Python 3.7+
- Flask, requests, pymysql: `pip install -r requirements.txt`
- Passwordless SSH access from your machine to all Jira app nodes and database server
- MySQL database access with read-only credentials
- Jira Personal Access Token (PAT) for API access
- Network access to Jira servers and database server

## Configuration

### Main Configuration File: `config.py`

Edit `config.py` to configure your environment:

#### Jira Server Configuration
```python
JIRA_SERVERS = [
    {"name": "Jira Server 1", "url": "http://jira-server-1.example.com:8080", "hostname": "jira-server-1.example.com"},
    {"name": "Jira Server 2", "url": "http://jira-server-2.example.com:8080", "hostname": "jira-server-2.example.com"},
    {"name": "Jira Server 3", "url": "http://jira-server-3.example.com:8080", "hostname": "jira-server-3.example.com"},
]
```

**Configuration Parameters:**
- `name`: Display name for the server in the dashboard
- `url`: Base URL of the Jira server (include port if not 80/443)
- `hostname`: Hostname for SSH access (must match actual server hostname)

#### Database Server Configuration
```python
DB_SERVER = {
    "name": "Database Server",
    "hostname": "db-server.example.com",
    "db_name": "jiradb",
    "db_user": "atlassian_readonly",
    "db_password": "TOKEN"  # Replace TOKEN with actual database password
}
```

**Configuration Parameters:**
- `hostname`: Database server hostname for SSH and MySQL access
- `db_name`: MySQL database name (typically "jiradb")
- `db_user`: MySQL username (read-only account recommended)
- `db_password`: **Replace "TOKEN" with actual database password**

#### Authentication
```python
JIRA_PAT = "TOKEN"  # Replace TOKEN with actual Jira Personal Access Token
SSH_USER = "your_ssh_user"  # Replace with your SSH username
```

**Configuration Parameters:**
- `JIRA_PAT`: **Replace "TOKEN" with actual Jira Personal Access Token**
  - Generate from: Jira → Account Settings → Security → API Tokens
- `SSH_USER`: **Replace with your SSH username** (must have passwordless SSH configured)

#### Auto-Refresh Configuration
```python
AUTO_REFRESH_INTERVAL = 120  # seconds (2 minutes)
```

**Configuration Parameters:**
- `AUTO_REFRESH_INTERVAL`: Refresh interval in seconds (default: 120 seconds / 2 minutes)
  - Recommended: 2-3 minutes to allow health checks to complete without overlap

#### Thresholds Configuration
```python
DB_CONNECTION_THRESHOLDS = {
    "green_max": 0.80,    # < 80% = Green
    "yellow_max": 0.90,  # 80-90% = Yellow
    # > 90% = Red
}

SYSTEM_THRESHOLDS = {
    "cpu": {"green_max": 70, "yellow_max": 85},
    "memory": {"green_max": 75, "yellow_max": 90},
    "swap": {"green_max": 50, "yellow_max": 80},
    "load": {"green_max": 1.0, "yellow_max": 2.0},
    "disk": {"green_max": 75, "yellow_max": 90}
}
```

**Threshold Parameters:**
- Adjust thresholds based on your environment and requirements
- Color coding: Green (< green_max), Yellow (green_max to yellow_max), Red (> yellow_max)

## How to Use

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure settings in config.py
# - Replace TOKEN placeholders with actual credentials
# - Update server hostnames and URLs
# - Configure SSH user
# - Adjust thresholds as needed
```

### 2. Configure Passwordless SSH

Ensure passwordless SSH is configured from your machine to all nodes:

```bash
# Generate SSH key (if not already done)
ssh-keygen -t rsa -b 4096

# Copy key to each server
ssh-copy-id your_ssh_user@jira-server-1.example.com
ssh-copy-id your_ssh_user@jira-server-2.example.com
ssh-copy-id your_ssh_user@jira-server-3.example.com
ssh-copy-id your_ssh_user@db-server.example.com

# Test connection
ssh your_ssh_user@jira-server-1.example.com "echo 'Connection successful'"
```

### 3. Run the Dashboard

```bash
# Start the Flask application
python3 app.py
```

The dashboard will be available at:
```
http://localhost:5001
```

### 4. Using the Dashboard

#### Monitoring Mode
- Click **"Monitoring"** to start automatic refresh every 2 minutes (configurable)
- Dashboard will auto-refresh and show real-time metrics
- Click **"Stop"** to stop auto-refresh

#### On-Demand Refresh
- Click **"On Demand"** for a one-time health check
- Useful for manual checks without continuous monitoring

#### JSON API
- Click **"JSON API"** to view raw JSON data
- Useful for debugging or integration with other tools
- API endpoint: `http://localhost:5001/api/health`

## Dashboard Sections

### 1. Jira Index Health
- **DB Count**: Total issues in database
- **Index Count**: Total issues in search index
- **Archive Count**: Total archived issues
- **Last Update**: Timestamps for database and index updates
- **Response Time**: API response time in seconds

### 2. System Metrics
- **CPU %**: CPU utilization percentage
- **Memory %**: RAM utilization percentage
- **Swap %**: Swap space utilization percentage
- **Load Avg**: 1-minute load average
- **Disk Usage (Local) %**: Local filesystem disk usage (`/export`)
- **Disk Usage (Shared Home) %**: Shared home disk usage (app nodes only, from `cluster.properties`)
- **Disk Usage (Binlogs) %**: MySQL binlogs disk usage (DB node only, `/mysqllogs`)

### 3. Database Connections
- **Active Connections**: Current database connections per node
- **Utilization**: Percentage of connection pool used
- **Threshold Status**: Color-coded status (Green/Yellow/Red)

### 4. Database Server Metrics
- **Total Connections**: Current connections vs max connections
- **Connection Utilization**: Overall connection pool utilization
- **Active Queries**: Number of non-Sleep queries
- **Slow Queries**: Count of slow queries from MySQL status

## Color Coding

### System Metrics
- **Green**: Normal operation (< threshold)
- **Yellow**: Warning (between thresholds)
- **Red**: Critical (> threshold)

### Database Connections
- **Green**: < 80% utilization
- **Yellow**: 80-90% utilization
- **Red**: > 90% utilization

## Server Names and Locations

### App Nodes
- **Hostname Pattern**: Should start with "jira-" (e.g., `jira-server-1.example.com`)
- **SSH Access**: Required for system metrics collection
- **Shared Home**: Automatically detected from `/export/jirahome/cluster.properties`
  - Reads `jira.shared.home` property
  - Tracks disk usage of the shared home path

### Database Node
- **Hostname Pattern**: Should start with "db-" (e.g., `db-server.example.com`)
- **SSH Access**: Required for system metrics collection
- **MySQL Access**: Required for database metrics
- **Binlogs Path**: `/mysqllogs` (configurable in code if different)

## Error Handling

- **Unreachable Nodes**: Show error status but don't block other nodes
- **SSH Timeouts**: Handled gracefully with error messages
- **Database Connection Failures**: Show error messages in database metrics section
- **Missing Configuration**: Shows "N/A" for unavailable metrics
- **All Errors**: Logged to `jira_health_dashboard.log` and displayed in UI

## Logging

Logs are written to:
- **File**: `jira_health_dashboard.log` (in the framework directory)
- **Console**: Standard output

Log levels:
- **INFO**: General operations, health check start/end, metric collection
- **WARNING**: Failed operations, missing data
- **ERROR**: Connection failures, critical errors
- **DEBUG**: Detailed command execution (if enabled)

## API Endpoints

- **`/`**: Main dashboard page
- **`/check-health`**: Manual health check endpoint (triggers full health check)
- **`/api/health`**: JSON API endpoint for programmatic access

### Example API Response
```json
{
  "index_health": [...],
  "system_metrics": [...],
  "db_connections": [...],
  "db_metrics": {...},
  "last_update": "2026-01-16 12:00:00"
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

### Database Connection Issues
- Verify database credentials in `config.py`
- Test MySQL connection: `mysql -h db-server.example.com -u atlassian_readonly -p jiradb`
- Check firewall rules for MySQL port (3306)

### Jira API Issues
- Verify Jira PAT is correct and not expired
- Test API access: `curl -H "Authorization: Bearer YOUR_PAT" http://jira-server-1.example.com:8080/rest/api/2/index/summary`
- Check Jira server is accessible from your machine

### Missing Shared Home Disk Usage
- Verify `/export/jirahome/cluster.properties` exists on app nodes
- Check `jira.shared.home` property is set correctly
- Verify shared home path is accessible and mount point exists

## Security Notes

- **Credentials**: All passwords and tokens are stored in `config.py` as placeholders ("TOKEN")
- **SSH Keys**: Use passwordless SSH with key-based authentication
- **Read-Only DB**: Use read-only database account for monitoring
- **Network**: Ensure dashboard server has network access to Jira and database servers
- **Production**: Consider using environment variables or secure vaults for credentials

## Future Enhancements

- Historical data tracking and trending
- Alert notifications (email, Slack, etc.)
- Customizable dashboard layouts
- Export functionality (CSV, PDF reports)
- Performance optimization (parallel SSH execution)
- Additional metrics (network I/O, JVM metrics, etc.)

## Support

For issues or questions:
1. Check logs: `jira_health_dashboard.log`
2. Verify configuration in `config.py`
3. Test SSH and database connections manually
4. Review error messages in dashboard UI
