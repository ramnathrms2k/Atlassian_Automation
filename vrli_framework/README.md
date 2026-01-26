# vRLI Hybrid Extraction Framework

## Overview

A sophisticated log extraction and query framework for VMware Aria Operations for Logs (vRLI). This framework overcomes vRLI API limitations by using a hybrid approach: server-side filtering with regex injection and client-side fallback extraction for 100% data reliability.

## What It Does

- **Automated Field Discovery**: Automatically discovers all extracted fields from vRLI API
- **Hybrid Extraction**: Server-side filtering + client-side Python regex fallback
- **Numeric Filtering**: Enables numeric filtering (e.g., `response_time >= 30000`) that standard API doesn't support
- **Data Reliability**: Ensures 100% data extraction with no null values
- **Flexible Queries**: Supports complex filters with multiple conditions
- **Multiple Output Formats**: CSV and JSON output support

## Prerequisites

- Python 3.7+
- Access to vRLI instance
- Active Directory credentials for authentication
- Network access to vRLI API endpoint

## Configuration

### Main Configuration File: `config.py`

Edit `config.py` to configure:

#### Connection Settings
```python
VRLI_HOST = "lvn-rnd-unix-logs.lvn.broadcom.net"
BASE_URL = f"https://{VRLI_HOST}:9543/api/v1"
```

**Configuration Parameters:**
- `VRLI_HOST`: vRLI server hostname or IP
- `BASE_URL`: vRLI API base URL (usually port 9543)

#### Field Definitions: `KNOWN_DEFINITIONS`

The framework automatically discovers fields from vRLI, but you can enhance extraction by adding regex patterns to `KNOWN_DEFINITIONS`:

```python
KNOWN_DEFINITIONS = {
    "Jira_ResponseTime_ms": { 
        "regexPreset": "INTEGER", 
        "preContext": "\" \\d+ (\\d+ |- )", 
        "postContext": " \"",
        "pyRegex": r'" \d+ (\d+ |- )(?P<val>-?\d+) "' 
    }
}
```

**Field Definition Parameters:**
- `regexPreset`: Standard regex pattern (INTEGER, IP4, DECIMAL, etc.)
- `preContext`: Text before the field value
- `postContext`: Text after the field value
- `pyRegex`: Python regex pattern for client-side extraction

### Server Names and Locations

- **vRLI Host**: Configured in `config.py` as `VRLI_HOST`
- **API Endpoint**: Automatically constructed from `VRLI_HOST`

### Thresholds

- **Query Limits**: Use `--limit` parameter (default: 100)
- **Time Ranges**: Use `--hours`, `--minutes`, or `--start`/`--end`
- **Filter Conditions**: Use `--filter` parameter with operators (>=, <=, =, !=, >, <)

## How to Use

### 1. Setup

```bash
# Install dependencies
pip install requests urllib3

# No additional configuration needed - field discovery is automatic
```

### 2. Basic Usage

```bash
# Query with filter
python3 main.py --filter "Jira_ResponseTime_ms>=30000" --hours 2

# Query with multiple filters
python3 main.py --filter "apptag=jira" --filter "Jira_ResponseTime_ms>=5000" --hours 24

# Output to CSV
python3 main.py --filter "Jira_UserID=rt033583" --hours 24 --format csv --output results.csv

# Output to JSON
python3 main.py --filter "Jira_ResponseTime_ms>=30000" --format json --output results.json
```

### 3. Authentication

The framework supports multiple authentication methods:

**Method 1: Interactive**
```bash
python3 main.py --filter "..." --hours 2
# Prompts for username and password
```

**Method 2: Command Line**
```bash
python3 main.py --filter "..." --hours 2 --auth-user "your_user" --password "your_pass"
```

**Method 3: Environment Variables**
```bash
export VRLI_USERNAME="your_user"
export VRLI_PASSWORD="your_pass"
python3 main.py --filter "..." --hours 2
```

### 4. Advanced Usage

```bash
# Specific time range
python3 main.py --filter "..." --start "2025-12-20 10:00:00" --end "2025-12-20 12:00:00"

# Select specific fields
python3 main.py --filter "..." --fields "datetime,host,Jira_ResponseTime_ms,JiraConf_Access_URI"

# Custom limit
python3 main.py --filter "..." --hours 2 --limit 1000
```

## Credentials/Tokens

### Authentication

- **Username**: Your Active Directory username
- **Password**: Your Active Directory password
- **Provider**: ActiveDirectory (configured in `auth.py`)

### Security Notes

- **Never commit credentials to version control**
- Use environment variables (`VRLI_USERNAME`, `VRLI_PASSWORD`) in production
- Consider using secure vaults for password management
- Passwords are not stored - only used for session token generation

## Field Discovery

The framework automatically discovers fields from vRLI API. To add new fields:

1. **Automatic Discovery**: Fields are discovered from `/api/v1/fields` endpoint
2. **Manual Enhancement**: Add regex patterns to `KNOWN_DEFINITIONS` in `config.py` for better extraction
3. **Client-Side Fallback**: Python regex patterns ensure extraction even if API fails

## Filter Syntax

### String Fields
```bash
--filter "Jira_UserID=rt033583"
--filter "Jira_UserID!=rt033583"
--filter "apptag=jira"
```

### Numeric Fields
```bash
--filter "Jira_ResponseTime_ms>=30000"
--filter "Jira_ResponseTime_ms<=1000"
--filter "Jira_ResponseTime_ms>5000"
--filter "http_code=200"
```

### Multiple Filters
```bash
--filter "apptag=jira" --filter "Jira_ResponseTime_ms>=30000" --filter "http_code!=200"
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify credentials and network connectivity
2. **No Results**: Check filter syntax and time range
3. **Field Not Found**: Field may not be discovered - check vRLI UI for field name
4. **Connection Errors**: Verify `VRLI_HOST` is correct and accessible

### Getting Help

- Check error messages in stderr output
- Verify field names match vRLI UI exactly
- Test with simple filters first, then add complexity

## Example Workflows

### Performance Incident Audit
```bash
# Find slow requests (>30 seconds) from last 5 days
python3 main.py \
  --filter "apptag=jira" \
  --filter "Jira_ResponseTime_ms>=30000" \
  --hours 120 \
  --fields "datetime,host,Jira_ResponseTime_ms,JiraConf_Access_URI" \
  --format csv \
  --output slow_queries.csv
```

### User Forensics
```bash
# Extract specific user activity
python3 main.py \
  --filter "apptag=jira" \
  --filter "Jira_UserID=rt033583" \
  --hours 24 \
  --format json \
  --output user_activity.json
```

## Files Overview

- `main.py`: CLI interface and entry point
- `engine.py`: Core extraction logic and field discovery
- `auth.py`: Authentication handling
- `config.py`: Configuration and field definitions

---

**Note**: This is production-ready code. Replace "TOKEN" placeholders if any exist, and configure `VRLI_HOST` for your environment.

