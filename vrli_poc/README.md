# vRLI POC (Proof of Concept)

## Overview

Proof of concept scripts for vRLI (VMware Aria Operations for Logs) log fetching, analysis, and statistics generation. These scripts demonstrate vRLI integration patterns and log analysis capabilities.

## What It Does

- **Log Fetching**: Fetches logs from vRLI using API
- **Field Discovery**: Discovers and tests vRLI extracted fields
- **Statistics Generation**: Generates access log statistics and analytics
- **Data Conversion**: Converts JSON log data to CSV format
- **Automated Workflows**: Provides shell scripts for automated log analysis

## Prerequisites

- Python 3.7+
- Access to vRLI instance
- Active Directory credentials
- Network access to vRLI API endpoint

## Configuration

### Authentication

Scripts support multiple authentication methods:

**Environment Variables:**
```bash
export VRLI_USERNAME="your_username"
export VRLI_PASSWORD="your_password"
```

**Command Line:**
```bash
--user "your_username" --password "your_password"
```

**Interactive:**
Scripts will prompt for credentials if not provided.

### Server Names and Locations

- **vRLI Host**: Configured in scripts (typically hardcoded or via environment)
- **API Endpoint**: Usually `https://<vRLI_HOST>:9543/api/v2`

### Thresholds

- **Query Limits**: Configured via `--limit` parameter (default varies by script)
- **Time Ranges**: Configured via `--hours` or `--days` parameters

## How to Use

### 1. Setup

```bash
# Install dependencies
pip install requests urllib3

# Set credentials (optional - can be provided at runtime)
export VRLI_USERNAME="your_username"
export VRLI_PASSWORD="your_password"
```

### 2. Run Scripts

```bash
# Fetch logs
python3 vrli_fetch.py --query "your_query" --hours 2

# Test field discovery
python3 vrli_fields_poc.py --request_fields "field1,field2"

# Generate access log statistics
python3 access_log_stats.py

# Generate access log statistics (debug mode)
python3 access_log_stats_debug.py

# Convert JSON to CSV
python3 json_to_csv_v2.py input.json output.csv

# Run automated statistics workflow
./run_stats.sh --hours 24

# Get logs (shell script wrapper)
./get_logs.sh
```

### 3. Authentication Options

```bash
# Using environment variables
export VRLI_USERNAME="user"
export VRLI_PASSWORD="pass"
python3 vrli_fetch.py --query "..." --hours 2

# Using command line
python3 vrli_fetch.py --query "..." --hours 2 --user "user" --password "pass"

# Interactive prompt
python3 vrli_fetch.py --query "..." --hours 2
# Will prompt for username and password
```

## Credentials/Tokens

### Authentication

- **Username**: Your Active Directory username
- **Password**: Your Active Directory password

### Security Notes

- **Never commit credentials to version control**
- Use environment variables for automation
- Passwords are not stored - only used for session tokens
- Consider using secure vaults for production

## Script Descriptions

### vrli_fetch.py
Fetches logs from vRLI using PIQL queries.

### vrli_fields_poc.py
Tests and discovers vRLI extracted fields.

### access_log_stats.py
Generates statistics from access logs.

### access_log_stats_debug.py
Debug version of access log statistics with additional logging.

### json_to_csv_v2.py
Converts JSON log data to CSV format.

### run_stats.sh
Automated workflow script for running statistics generation.

### get_logs.sh
Shell script wrapper for log fetching.

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify credentials and network connectivity
2. **Query Errors**: Check PIQL query syntax
3. **No Results**: Verify time range and query parameters
4. **Connection Errors**: Check vRLI host and network connectivity

### Getting Help

- Review error messages in console output
- Verify vRLI API endpoint is accessible
- Test authentication manually first

## Example Workflow

```bash
# 1. Set credentials
export VRLI_USERNAME="your_user"
export VRLI_PASSWORD="your_pass"

# 2. Fetch logs
python3 vrli_fetch.py --query "apptag:jira" --hours 24

# 3. Generate statistics
python3 access_log_stats.py

# 4. Convert to CSV
python3 json_to_csv_v2.py logs.json logs.csv

# 5. Run automated workflow
./run_stats.sh --hours 24
```

## Files Overview

- `vrli_fetch.py`: Log fetching script
- `vrli_fields_poc.py`: Field discovery and testing
- `access_log_stats.py`: Access log statistics generation
- `access_log_stats_debug.py`: Debug version of statistics
- `json_to_csv_v2.py`: JSON to CSV converter
- `run_stats.sh`: Automated statistics workflow
- `get_logs.sh`: Log fetching wrapper script

---

**Note**: This is production-ready code. Configure vRLI host and credentials before execution.

