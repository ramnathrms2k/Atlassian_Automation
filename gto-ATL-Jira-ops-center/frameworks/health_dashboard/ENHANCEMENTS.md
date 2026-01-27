# Jira Health Dashboard - Enhancements Summary

## Overview
Enhanced the Jira Health Dashboard to include comprehensive system metrics, database connection monitoring, and auto-refresh functionality.

## New Features

### 1. System Metrics Monitoring
- **CPU Utilization %**: Real-time CPU usage per server
- **Memory Utilization %**: RAM usage tracking
- **Swap Utilization %**: Swap space usage
- **Load Average**: 1-minute load average
- **Disk Usage %**: Disk space utilization (prioritizes /export/jira)

### 2. Database Connection Tracking
- **Per App Node**: Shows active DB connections from each Jira app node
- **DB Server Total**: Shows total connections on database server
- **Connection Utilization**: Percentage of pool/max connections used
- **Color-coded Thresholds**: 
  - Green: < 80% utilization
  - Yellow: 80-90% utilization
  - Red: > 90% utilization

### 3. Database Metrics (DB Server Only)
- Total connections vs max connections
- Connection utilization percentage
- Active queries count
- Slow queries count

### 4. Auto-Refresh
- Automatic refresh every 30 seconds (configurable)
- Toggle on/off checkbox
- Manual refresh button
- JSON API endpoint for programmatic access

### 5. Enhanced UI/UX
- Categorized sections with clear headers
- Color-coded status indicators
- Responsive table layout
- Last update timestamp
- Error handling for unreachable nodes

## Configuration

### Files Modified
1. **config.py**: Added thresholds, SSH config, DB credentials, refresh interval
2. **app.py**: Added SSH functions, system metrics, DB metrics collection
3. **templates/index.html**: Complete redesign with multiple sections
4. **requirements.txt**: Added dependencies (Flask, requests, pymysql)

### Configuration Options (config.py)
- `AUTO_REFRESH_INTERVAL`: Refresh interval in seconds (default: 30)
- `DB_CONNECTION_THRESHOLDS`: Connection utilization thresholds
- `SYSTEM_THRESHOLDS`: CPU, memory, swap, load, disk thresholds
- `SSH_USER`: SSH username (svcjira)
- `SSH_TIMEOUT`: SSH connection timeout (10 seconds)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure settings in `config.py`:
   - Update JIRA_PAT if needed
   - Adjust thresholds as needed
   - Verify SSH user and hostnames

3. Run the application:
```bash
python3 app.py
```

4. Access the dashboard:
```
http://localhost:5001
```

## Prerequisites

1. **Passwordless SSH**: Must be configured from your Mac to all nodes as user `svcjira`
2. **Python 3.7+**: Required for async/await support
3. **Network Access**: Access to Jira servers and database server
4. **MySQL Access**: Database credentials configured in config.py

## Monitoring Capabilities

### Jira Index Health
- Database count, index count, archive count
- Last update timestamps
- API response times

### System Metrics
- CPU, memory, swap, load, disk usage
- Color-coded based on thresholds
- Per-server monitoring

### Database Connections
- App node connections (client-side)
- DB server total connections (server-side)
- Utilization percentages
- Threshold-based alerts

### Database Metrics
- Connection pool status
- Active queries
- Slow queries
- Connection utilization

## Thresholds

### Database Connections
- **Green**: < 80% (App: < 200, Total: < 1200)
- **Yellow**: 80-90% (App: 200-225, Total: 1200-1350)
- **Red**: > 90% (App: > 225, Total: > 1350)

### System Metrics
- **CPU**: Green < 70%, Yellow 70-85%, Red > 85%
- **Memory**: Green < 75%, Yellow 75-90%, Red > 90%
- **Swap**: Green < 50%, Yellow 50-80%, Red > 80%
- **Load**: Green < 1.0, Yellow 1.0-2.0, Red > 2.0
- **Disk**: Green < 75%, Yellow 75-90%, Red > 90%

## API Endpoints

- `/`: Main dashboard page
- `/check-health`: Manual refresh endpoint
- `/api/health`: JSON API endpoint for programmatic access

## Error Handling

- Unreachable nodes show error status but don't block other nodes
- SSH timeouts handled gracefully
- Database connection failures show error messages
- All errors are logged and displayed in UI

## Future Enhancements

- Historical data tracking
- Trend indicators (↑↓)
- Export to CSV functionality
- Email/Slack alerts
- Custom dashboard views
- Performance graphs
