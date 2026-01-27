# GTO ATL Jira Operations Center

A unified dashboard for managing and monitoring multiple Jira Data Center instances across different environments.

## Overview

This framework consolidates multiple Jira automation tools into a single, multi-instance capable operations center. It provides a unified interface to:

- **Health Dashboard**: Comprehensive health monitoring for Jira clusters
- **Response Time Tracker**: Monitor slow requests from Jira access logs
- **Preflight Validator**: Pre-deployment validation for Jira Data Center nodes
- **Script Executor**: Execute scripts on multiple servers via SSH

## Features

- **Multi-Instance Support**: Switch between different Jira environments (Production, Staging, etc.)
- **Unified Interface**: Single entry point for all frameworks
- **Centralized Configuration**: Manage all instance configurations in one place
- **Easy Onboarding**: Add new instances by updating `instances_config.py`

## Installation

1. **Navigate to the framework directory**:
   ```bash
   cd atlassian-automation/gto-ATL-Jira-ops-center
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure instances**:
   - Edit `instances_config.py` to add your Jira instances
   - Update credentials (or use environment variables)

4. **Set environment variables** (optional, for credentials):
   ```bash
   export JIRA_OPS_VMW_JIRA_PROD_JIRA_PAT="your_token_here"
   export JIRA_OPS_VMW_JIRA_PROD_DB_PASSWORD="your_password_here"
   ```

## Configuration

### Instance Configuration

Edit `instances_config.py` to configure your Jira instances:

```python
INSTANCES = {
    "vmw-jira-prod": {
        "display_name": "VMW-Jira-Prod",
        "description": "VMware Jira Production Environment",
        "jira_servers": [...],
        "db_server": {...},
        # ... more configuration
    }
}
```

### Adding New Instances (Onboarding Procedure)

To onboard a new Jira environment/instance to the Operations Center:

#### Step 1: Prepare Instance Information

Gather the following information for your new instance:
- **Instance ID**: A unique identifier (e.g., `vmw-jira-staging`, `vmw-jira-dev`)
- **Display Name**: Human-readable name (e.g., "VMW-Jira-Staging")
- **Jira Application Servers**: List of all Jira app nodes with:
  - Server names/descriptions
  - Hostnames (FQDNs)
  - Base URLs (e.g., `http://hostname:8080`)
  - Access log paths
- **Database Server**: 
  - Hostname
  - Database name
  - Database user (read-only recommended)
  - Database password
- **SSH Configuration**:
  - SSH user (must have passwordless SSH configured)
  - SSH timeout
- **Jira Configuration**:
  - Jira version
  - Installation directory path
  - Jira home directory path
  - Shared home path (for Data Center)
- **Credentials**:
  - Jira Personal Access Token (PAT)
  - Database password
- **Thresholds and Settings**: Framework-specific thresholds (optional, defaults will be used)

#### Step 2: Add Instance to Configuration

1. **Open `instances_config.py`** in the framework root directory

2. **Add a new entry** to the `INSTANCES` dictionary:

```python
INSTANCES = {
    "vmw-jira-prod": {
        # ... existing configuration ...
    },
    
    # Add your new instance here
    "your-instance-id": {
        "display_name": "Your Display Name",
        "description": "Description of the environment",
        
        "jira_servers": [
            {
                "name": "Jira Server 1",
                "hostname": "jira-server-1.example.com",
                "url": "http://jira-server-1.example.com:8080",
                "log_path": "/export/jira/logs"
            },
            # Add more servers as needed
        ],
        
        "db_server": {
            "name": "Database Server",
            "hostname": "db-server.example.com",
            "db_name": "jiradb",
            "db_user": "atlassian_readonly",
            "db_password": "TOKEN"  # Use environment variable
        },
        
        "ssh": {
            "user": "svcjira",
            "timeout": 10
        },
        
        "paths": {
            "jira_install": "/export/jira",
            "jira_home": "/export/jirahome",
            "log_path": "/export/jira/logs",
            "shared_home": "/projects/atlassian-jira/sharehome"
        },
        
        "credentials": {
            "jira_pat": "TOKEN",  # Use environment variable
            "db_password": "TOKEN"  # Use environment variable
        },
        
        "jira": {
            "version": "10.3.12",
            "db_validation_user": "atlassian_readonly"
        },
        
        "thresholds": {
            "db_max_connections": 1500,
            "db_pool_per_app_node": 250,
            "response_time_ms": 60000,
            "tail_lines": 5000,
            "jira_api_timeout": 60,
            "db_connect_timeout": 10,
            "db_read_timeout": 30,
            # Add framework-specific thresholds as needed
        },
        
        "settings": {
            "access_log_format": "access_log.%Y-%m-%d",
            "auto_refresh_interval": 120,
            "refresh_interval": 5,
            "script_dir": "/export/scripts/",
            "script_name": "monitor_jira_v22.sh",
            "script_timeout": 20
        }
    }
}
```

#### Step 3: Configure Credentials (Security Best Practice)

**Option A: Environment Variables (Recommended)**

Set environment variables for credentials:

```bash
export JIRA_OPS_YOUR_INSTANCE_ID_JIRA_PAT="your_actual_token"
export JIRA_OPS_YOUR_INSTANCE_ID_DB_PASSWORD="your_actual_password"
```

The environment variable naming convention is:
- `JIRA_OPS_<INSTANCE_ID>_JIRA_PAT` (replace `<INSTANCE_ID>` with your instance ID in uppercase)
- `JIRA_OPS_<INSTANCE_ID>_DB_PASSWORD`

Example for `vmw-jira-staging`:
```bash
export JIRA_OPS_VMW_JIRA_STAGING_JIRA_PAT="your_token"
export JIRA_OPS_VMW_JIRA_STAGING_DB_PASSWORD="your_password"
```

**Option B: Direct Configuration (Not Recommended for Production)**

If you must use direct configuration (not recommended), replace `"TOKEN"` with actual values in `instances_config.py`. **Never commit actual credentials to git.**

#### Step 4: Verify SSH Access

Ensure passwordless SSH is configured from your machine to all servers:

```bash
# Test SSH access to each server
ssh svcjira@jira-server-1.example.com "echo 'Connection successful'"
ssh svcjira@jira-server-2.example.com "echo 'Connection successful'"
ssh svcjira@db-server.example.com "echo 'Connection successful'"
```

#### Step 5: Test the Configuration

1. **Restart the application**:
   ```bash
   python app.py
   ```

2. **Verify the new instance appears**:
   - Open browser to `http://localhost:8000`
   - Select any framework
   - Check that your new instance appears in the instance dropdown

3. **Test framework functionality**:
   - Launch each framework with your new instance
   - Verify data loads correctly
   - Check that all servers are accessible

#### Step 6: Framework-Specific Configuration

Some frameworks may require additional configuration:

- **Preflight Validator**: Ensure `jira_node_validator_v10.py` is in the framework directory
- **Script Executor**: Verify script paths and names match your environment
- **Health Dashboard**: Verify database connectivity and Jira API access
- **Response Tracker**: Verify access log paths and format match your setup

#### Troubleshooting New Instance Onboarding

- **Instance not appearing**: Check `instances_config.py` syntax, ensure all required fields are present
- **SSH connection failures**: Verify passwordless SSH is configured correctly
- **Database connection errors**: Check database credentials and network connectivity
- **Jira API errors**: Verify Jira PAT is valid and has necessary permissions
- **Framework not loading**: Check application logs for specific error messages

#### Example: Complete Instance Configuration

See the `vmw-jira-prod` entry in `instances_config.py` as a complete reference example.

## Usage

### Starting the Application

```bash
python app.py
```

The application will start on `http://localhost:8000` (or the port specified by `PORT` environment variable).

### Using the Dashboard

1. **Open the browser** and navigate to `http://localhost:8000`
2. **Select a framework** from the main page (Health Dashboard, Response Tracker, etc.)
3. **Select an instance** from the dropdown (e.g., VMW-Jira-Prod)
4. **Click "Launch Framework"** to start using the selected tool

### Framework-Specific Usage

#### Health Dashboard
- Monitor Jira index health
- View system metrics (CPU, memory, disk, load)
- Track database connections
- Auto-refresh capability

#### Response Time Tracker
- Analyze slow requests from access logs
- View user-based statistics
- Monitor across multiple Jira nodes

#### Preflight Validator
- Validate node configuration before deployment
- Compare node identities
- Generate validation reports

#### Script Executor
- Execute scripts on multiple servers
- Parallel execution with real-time output
- Threshold-based alerting

## Environment Variables

For secure credential management, use environment variables:

- `JIRA_OPS_<INSTANCE_ID>_JIRA_PAT`: Jira Personal Access Token
- `JIRA_OPS_<INSTANCE_ID>_DB_PASSWORD`: Database password

Example:
```bash
export JIRA_OPS_VMW_JIRA_PROD_JIRA_PAT="your_token"
export JIRA_OPS_VMW_JIRA_PROD_DB_PASSWORD="your_password"
```

## Testing

### Basic Test

1. Start the application:
   ```bash
   python app.py
   ```

2. Open browser to `http://localhost:8000`

3. Verify:
   - Main page loads with 4 framework cards
   - Clicking a framework shows instance selection
   - Selecting an instance and clicking "Launch" works

### Framework Testing

1. **Health Dashboard**:
   - Select "Health Dashboard" → "VMW-Jira-Prod" → Launch
   - Verify health data loads
   - Check that all 3 app nodes and DB server appear

2. **Response Tracker**:
   - Select "Response Time Tracker" → "VMW-Jira-Prod" → Launch
   - Verify slow request statistics display

3. **Preflight Validator**:
   - Select "Preflight Validator" → "VMW-Jira-Prod" → Launch
   - Verify node validation works

4. **Script Executor**:
   - Select "Script Executor" → "VMW-Jira-Prod" → Launch
   - Verify script execution interface loads

## Troubleshooting

### Framework Not Loading

- Check that the framework module exists in `frameworks/` directory
- Verify `instances_config.py` has valid configuration
- Check application logs for errors

### Configuration Issues

- Ensure `instances_config.py` has all required fields
- Verify credentials are set (either in config or environment variables)
- Check that server hostnames are correct

### SSH Connection Issues

- Verify passwordless SSH is configured
- Check SSH user (`svcjira`) has access
- Test SSH connection manually: `ssh svcjira@<hostname>`

## Architecture

```
gto-ATL-Jira-ops-center/
├── app.py                 # Main launcher
├── instances_config.py    # Instance configurations
├── config_manager.py     # Configuration injection
├── templates/            # Main UI templates
│   ├── main.html         # Framework selection
│   └── select_instance.html  # Instance selection
├── frameworks/           # Framework modules
│   ├── health_dashboard/
│   ├── response_tracker/
│   ├── preflight_validator/
│   └── script_executor/
└── requirements.txt
```

## Security Notes

- **Credentials**: Never commit actual credentials to git
- **Use TOKEN placeholders** in `instances_config.py`
- **Use environment variables** for production credentials
- **Restrict access** to the application server

## Future Enhancements

- Historical data storage
- Alerting and notifications
- Scheduled tasks
- Multi-instance operations
- RESTful API

## Support

For issues or questions, refer to the individual framework documentation or contact the development team.
