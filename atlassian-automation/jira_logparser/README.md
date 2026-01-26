# Jira Log Parser

## Overview

A comprehensive log analysis framework for Jira access logs and application logs. This framework provides user activity analysis, system analytics, performance monitoring, and diagnostic capabilities.

## What It Does

- **User Activity Analysis**: Analyzes user activity patterns from access logs
- **Performance Monitoring**: Monitors Jira performance metrics and response times
- **System Analytics**: Provides hourly and daily system analytics
- **Slow Request Detection**: Identifies slow requests and performance bottlenecks
- **Diagnostic Bundle Generation**: Creates diagnostic bundles for troubleshooting
- **Apdex Calculation**: Calculates Apdex scores for performance measurement

## Prerequisites

- Bash shell
- Access to Jira log files
- Optional: Database access for advanced analytics
- Optional: SSH access to Jira nodes for remote log analysis

## Configuration

### Main Script: `monitor_jira_v22.sh`

Edit `monitor_jira_v22.sh` to configure log paths and thresholds:

```bash
LOG_FILE="/export/jira/logs/access_log.${CURRENT_DATE}"
APP_LOG_PATH="/export/jirahome/log"
DB_SERVER="db-lvnv-it-101.lvn.broadcom.net"
NUM_LINES="10000"
THRESHOLD_MS="10000"
REFRESH_INTERVAL="60"
GENERATE_BUNDLE="${GENERATE_BUNDLE:-true}"
LOG_ROTATION_BUFFER_MINUTES="${LOG_ROTATION_BUFFER_MINUTES:-5}"
```

**Configuration Parameters:**
- `LOG_FILE`: Path to Jira access log file (with date pattern)
- `APP_LOG_PATH`: Path to Jira application logs directory
- `DB_SERVER`: Database server hostname (if database analytics enabled)
- `NUM_LINES`: Number of log lines to analyze
- `THRESHOLD_MS`: Threshold for slow request detection (milliseconds)
- `REFRESH_INTERVAL`: Refresh interval for continuous monitoring (seconds)
- `GENERATE_BUNDLE`: Enable/disable diagnostic bundle generation
- `LOG_ROTATION_BUFFER_MINUTES`: Buffer time for log rotation handling

### Server Names and Locations

- **Log File Path**: Configured in scripts as `LOG_FILE`
- **Application Log Path**: Configured as `APP_LOG_PATH`
- **Database Server**: Configured as `DB_SERVER` (if database analytics used)

### Thresholds

- **Slow Request Threshold**: Configured as `THRESHOLD_MS` (default: 10000ms = 10 seconds)
- **Analysis Depth**: Configured as `NUM_LINES` (number of log lines to analyze)
- **Apdex Threshold**: Built into Apdex calculation (typically 4x target response time)

## How to Use

### 1. Setup

```bash
# Configure log paths in monitor_jira_v22.sh
# Update LOG_FILE and APP_LOG_PATH to match your Jira installation
```

### 2. Run Analysis

```bash
# Comprehensive monitoring (main script)
./monitor_jira_v22.sh

# User activity analysis (simple)
./analyze_user_simple.sh

# User activity analysis (new version)
./analyze_user_simple_new.sh

# User activity analysis (detailed)
./analyze_user_activity.sh

# User activity analysis (new detailed version)
./analyze_user_activity_new.sh

# Daily user analytics
./daily_user_analytics.sh

# Hourly system analytics
./hourly_system_analytics.sh
```

### 3. Command Line Options

Some scripts support command line options:

```bash
# Disable bundle generation (faster)
./monitor_jira_v22.sh --no-bundle

# Disable validation (faster)
./monitor_jira_v22.sh --no-validation

# Help
./monitor_jira_v22.sh --help
```

## Credentials/Tokens

### Database Credentials (Optional)

If database analytics are enabled, configure database credentials in scripts or environment variables.

### Security Notes

- **Log files may contain sensitive information** - handle with care
- **Never commit log files to version control**
- Use read-only database access if database analytics enabled

## Analysis Features

### User Activity Analysis

- User login patterns
- Most active users
- User request patterns
- User-specific slow requests

### Performance Monitoring

- Response time analysis
- Apdex score calculation
- Slow request identification
- Request pattern analysis

### System Analytics

- Hourly system metrics
- Daily user analytics
- Request volume analysis
- Error rate monitoring

## Troubleshooting

### Common Issues

1. **Log File Not Found**: Verify `LOG_FILE` path is correct and file exists
2. **Permission Denied**: Ensure read access to log files
3. **Database Connection Failed**: Check database configuration if using database analytics
4. **Large Log Files**: Adjust `NUM_LINES` or use log rotation

### Getting Help

- Review error messages in console output
- Verify log file paths and permissions
- Check database connectivity if using database features

## Example Workflow

```bash
# 1. Configure log paths
# Edit monitor_jira_v22.sh with your Jira log locations

# 2. Run monitoring
./monitor_jira_v22.sh

# 3. Analyze user activity
./analyze_user_activity_new.sh

# 4. Generate daily analytics
./daily_user_analytics.sh

# 5. Review output
# Check console output and generated reports
```

## Files Overview

- `monitor_jira_v22.sh`: Main comprehensive monitoring script
- `analyze_user_simple.sh`: Simple user activity analysis
- `analyze_user_simple_new.sh`: Enhanced simple user analysis
- `analyze_user_activity.sh`: Detailed user activity analysis
- `analyze_user_activity_new.sh`: Enhanced detailed user analysis
- `daily_user_analytics.sh`: Daily user analytics report
- `hourly_system_analytics.sh`: Hourly system analytics report

---

**Note**: This is production-ready code. Configure log file paths in scripts to match your Jira installation.

