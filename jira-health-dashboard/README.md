# Jira Health Dashboard

## Overview

A Flask-based web dashboard for monitoring the health and index status of multiple Jira Data Center servers. This framework provides real-time visibility into Jira index synchronization, database counts, and server response times across your Jira cluster.

## What It Does

- **Multi-Server Monitoring**: Monitors health status of multiple Jira servers simultaneously
- **Index Health Checks**: Fetches index summary data including database count, index count, and archive count
- **Response Time Tracking**: Measures API response times for each server
- **Status Visualization**: Web-based dashboard with color-coded status indicators
- **Real-Time Updates**: On-demand health checks with refresh capability
- **Error Handling**: Graceful error handling for connection issues, timeouts, and API errors

## Prerequisites

### Software Requirements
- **Python**: 3.7 or higher
- **Flask**: Web framework (install via pip)
- **requests**: HTTP library for API calls (install via pip)
- **Operating System**: Linux, macOS, or Windows (with WSL recommended)
- **Web Browser**: Modern web browser for accessing the dashboard

### Connectivity Requirements
- **Network Access**:
  - Network connectivity to Jira Data Center servers
  - Access to Jira REST API endpoints (typically port 8080 or 8443)
  - HTTP/HTTPS access to Jira base URLs
- **API Access**:
  - Jira REST API access (`/rest/api/2/index/summary`)
  - Personal Access Token (PAT) or API token with read permissions

### Folder Structure
The framework expects the following structure:
```
jira-health-dashboard/
├── app.py                    # Main Flask application
├── config.py                 # Server configuration and credentials
├── templates/
│   └── index.html           # Dashboard HTML template
└── README.md                 # This file
```

**Important**:
- `config.py` must be configured with your Jira servers and PAT
- Replace "TOKEN" placeholder in `config.py` with actual Personal Access Token
- Ensure Flask and requests are installed: `pip install flask requests`

### Access & Credentials
- **Jira API Access**:
  - Personal Access Token (PAT) configured in `config.py`
  - Token must have read access to Jira REST API
  - Replace "TOKEN" placeholder with actual token
- **Network Permissions**:
  - Network access to Jira server URLs
  - Firewall rules allowing HTTP/HTTPS to Jira ports

### Pre-Execution Checks
Before running the dashboard, verify:
1. ✅ Python 3.7+ installed: `python3 --version`
2. ✅ Flask installed: `pip install flask requests`
3. ✅ Jira servers accessible: `curl -I <JIRA_URL>`
4. ✅ PAT configured: Edit `config.py` and replace "TOKEN" with actual token
5. ✅ Server URLs correct: Verify URLs in `config.py` match your environment
6. ✅ Port available: Ensure port 5001 (or configured port) is available
7. ✅ Network connectivity: Test API access: `curl -H "Authorization: Bearer TOKEN" <JIRA_URL>/rest/api/2/index/summary`

## Configuration

### Configuration File: `config.py`

Edit `config.py` to configure your Jira servers and credentials:

```python
# --- Jira Server Configuration ---
JIRA_SERVERS = [
    {"name": "Jira Server 1 (Prod A)", "url": "http://jira-lvnv-it-101.lvn.broadcom.net:8080"},
    {"name": "Jira Server 2 (Prod B)", "url": "http://jira-lvnv-it-102.lvn.broadcom.net:8080"},
    {"name": "Jira Server 3 (Prod C)", "url": "http://jira-lvnv-it-103.lvn.broadcom.net:8080"},
]

# --- Personal Access Token ---
JIRA_PAT = "TOKEN"  # Replace TOKEN with actual Personal Access Token
```

**Configuration Parameters:**
- `JIRA_SERVERS`: List of dictionaries with server name and URL
  - `name`: Display name for the server (shown in dashboard)
  - `url`: Base URL of Jira server (include protocol and port)
- `JIRA_PAT`: Personal Access Token for Jira API authentication
  - **Important**: Replace "TOKEN" with actual token before use

### Server Names and Locations

- **Jira Server URLs**: Configured in `JIRA_SERVERS` list in `config.py`
- **Dashboard URL**: `http://0.0.0.0:5001` (or configured host/port)
- **API Endpoint**: `/rest/api/2/index/summary` (automatically appended to base URL)

### Thresholds

- **Request Timeout**: 10 seconds per server (configurable in `app.py`)
- **Concurrent Checks**: All servers checked sequentially
- **Refresh Rate**: Manual refresh via button click (on-demand)

## How to Use

### 1. Setup

```bash
# Install dependencies
pip install flask requests

# Configure servers and token in config.py
# Edit config.py and replace "TOKEN" with actual PAT
# Update JIRA_SERVERS list with your Jira server URLs
```

### 2. Run Dashboard

```bash
# Start the Flask application
python3 app.py
```

### 3. Access Dashboard

Open your web browser and navigate to:
```
http://localhost:5001
```

Or if running on a remote server:
```
http://<server-ip>:5001
```

### 4. Check Health Status

1. Click the "Run Health Check" button
2. Wait for all servers to be checked
3. Review the health status table with:
   - Server name
   - Status (Online or error message)
   - Check time
   - Database count
   - Index count
   - Archive count
   - Last update timestamps
   - Response time

## Credentials/Tokens

### Personal Access Token (PAT)

- **Location**: Configured in `config.py` as `JIRA_PAT`
- **Required**: Replace "TOKEN" placeholder with actual Personal Access Token
- **Permissions**: Token must have read access to Jira REST API
- **Security**: Never commit actual tokens to version control

### Creating a PAT

1. Log in to Jira
2. Go to Account Settings → Security → API Tokens
3. Create a new API token
4. Copy the token and replace "TOKEN" in `config.py`

### Security Notes

- **Never commit tokens to version control** - All tokens are sanitized (replaced with "TOKEN")
- **Use environment variables** - Consider loading PAT from environment variable for better security
- **Read-only access recommended** - Use tokens with minimal required permissions
- **Rotate tokens periodically** - Follow your organization's token rotation policies

## Dashboard Features

### Health Status Display
- **Online Status**: Green indicator when server is accessible
- **Error Status**: Red indicator with error message for failures
- **Response Time**: Shows API response time in seconds

### Index Information
- **Database Count**: Number of issues in database
- **Index Count**: Number of issues in search index
- **Archive Count**: Number of archived issues
- **Last Updated**: Timestamps for database and index updates

### Error Handling
- **Connection Errors**: Detects network connectivity issues
- **Timeout Handling**: Handles slow or unresponsive servers
- **HTTP Errors**: Displays HTTP error codes (401, 404, 500, etc.)
- **Graceful Degradation**: Shows error message instead of crashing

## Troubleshooting

### Common Issues

1. **Connection Error**: Cannot connect to Jira server
   - **Solution**: Check network connectivity and firewall rules
   - **Check**: `curl -I <JIRA_URL>` to test connectivity

2. **401 Unauthorized**: Invalid or expired PAT
   - **Solution**: Verify PAT is correct and has not expired
   - **Check**: Test token with: `curl -H "Authorization: Bearer TOKEN" <JIRA_URL>/rest/api/2/index/summary`

3. **404 Not Found**: API endpoint not available
   - **Solution**: Verify Jira version supports `/rest/api/2/index/summary` endpoint
   - **Check**: Confirm Jira server URL is correct

4. **Timeout**: Server not responding within 10 seconds
   - **Solution**: Server may be under heavy load or network issues
   - **Check**: Test server response time manually

5. **Port Already in Use**: Port 5001 is already occupied
   - **Solution**: Change port in `app.py` or stop conflicting service
   - **Check**: `lsof -i :5001` to find process using port

### Getting Help

- Review error messages in browser console (F12)
- Check Flask application logs in terminal
- Verify PAT and server URLs in `config.py`
- Test API access manually with curl

## Example Workflow

```bash
# 1. Install dependencies
pip install flask requests

# 2. Configure servers and token
# Edit config.py:
#   - Add your Jira server URLs to JIRA_SERVERS
#   - Replace "TOKEN" with actual PAT

# 3. Start dashboard
python3 app.py

# 4. Open browser
# Navigate to http://localhost:5001

# 5. Run health check
# Click "Run Health Check" button

# 6. Review results
# Check status, counts, and response times for each server
```

## Files Overview

- `app.py`: Main Flask application with health check logic and API endpoints
- `config.py`: Configuration file with Jira server URLs and Personal Access Token
- `templates/index.html`: HTML template for the web dashboard

---

**Note**: This is production-ready code. Replace "TOKEN" placeholder in `config.py` with actual Personal Access Token before use.
