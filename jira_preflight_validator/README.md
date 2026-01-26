# Jira Preflight Validator

## Overview

A comprehensive pre-deployment validation framework for Jira Data Center nodes. This framework validates Jira installations, configurations, database connectivity, and system requirements before deployment or upgrades.

## What It Does

- **Multi-Server Validation**: Validates multiple Jira nodes in parallel
- **Installation Verification**: Checks Jira binary version, installation directory, and file integrity
- **Configuration Validation**: Validates Jira configuration files and settings
- **Database Connectivity**: Tests database connections and queries
- **System Requirements**: Verifies CPU, memory, disk space, and other system requirements
- **Automated Reporting**: Generates comprehensive validation reports

## Prerequisites

- Python 3.7+
- SSH access to Jira application nodes
- Database read-only credentials
- Network connectivity to target servers

## Configuration

### Main Configuration File: `config.py`

Edit `config.py` to configure:

#### SSH Connectivity
```python
SSH_USER = "svcjira"
HOSTS = [
    "jira-lvnv-it-101.lvn.broadcom.net",
    "jira-lvnv-it-102.lvn.broadcom.net",
    "jira-lvnv-it-103.lvn.broadcom.net"
]
```

**Configuration Parameters:**
- `SSH_USER`: SSH username for connecting to nodes
- `HOSTS`: List of Jira node hostnames or IPs

#### Jira Configuration
```python
JIRA_VERSION = "10.3.12"
JIRA_INSTALL_DIR = "/export/jira"
DB_VALIDATION_USER = "atlassian_readonly"
```

**Configuration Parameters:**
- `JIRA_VERSION`: Expected Jira version
- `JIRA_INSTALL_DIR`: Jira installation directory path
- `DB_VALIDATION_USER`: Database user for validation queries

#### Database Password
```python
DB_PASSWORD = "TOKEN"
```

**Important**: Replace "TOKEN" with actual database password, or use environment variable `ATLASSIAN_DB_PASSWORD`.

#### Report Directory
```python
REPORT_DIR = os.path.join(os.getcwd(), "reports")
```

**Configuration Parameters:**
- `REPORT_DIR`: Directory where validation reports are saved

### Server Names and Locations

- **Jira Nodes**: Configured in `config.py` as `HOSTS` array
- **Database Server**: Configured in validation scripts
- **Installation Directory**: Configured as `JIRA_INSTALL_DIR`

### Thresholds

- **Version Matching**: Exact version match required (configured in `JIRA_VERSION`)
- **Disk Space**: Validated against minimum requirements
- **Memory**: Validated against Jira system requirements
- **Database Connectivity**: Connection timeout and query validation

## How to Use

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure servers and credentials in config.py
# Replace "TOKEN" with actual database password
```

### 2. Run Validation

```bash
# Single server validation
python3 jira_node_validator_v10.py

# Multi-server validation (parallel execution)
python3 multi_server_executor_v2.py

# Web interface (if app.py is available)
python3 app.py
```

### 3. Environment Variables

You can override configuration using environment variables:

```bash
export ATLASSIAN_DB_PASSWORD="your_password"
export JIRA_VERSION="10.3.12"
export JIRA_INSTALL_DIR="/export/jira"
python3 jira_node_validator_v10.py
```

## Credentials/Tokens

### Database Credentials

- **Username**: Configured as `DB_VALIDATION_USER` in `config.py`
- **Password**: Set in `config.py` as `DB_PASSWORD` or use `ATLASSIAN_DB_PASSWORD` environment variable
- **Replace "TOKEN"**: Replace "TOKEN" placeholder with actual database password

### SSH Credentials

- **SSH User**: Configured as `SSH_USER` in `config.py`
- **SSH Key**: Use passwordless SSH (set up SSH keys as per your organization's standards)

### Security Notes

- **Never commit passwords to version control**
- Use environment variables for passwords in production
- Use read-only database user for validation
- Rotate credentials periodically

## Validation Checks

The framework performs the following validations:

1. **Binary Version**: Verifies Jira binary version matches expected version
2. **Installation Directory**: Checks installation directory exists and is accessible
3. **Configuration Files**: Validates `jira-config.properties` and other config files
4. **Database Connectivity**: Tests database connection and runs sample queries
5. **System Resources**: Checks CPU, memory, disk space
6. **File Integrity**: Verifies critical Jira files are present and correct

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**: Verify SSH keys are set up and `SSH_USER` is correct
2. **Database Connection Failed**: Check database password and network connectivity
3. **Version Mismatch**: Update `JIRA_VERSION` in `config.py` to match actual version
4. **Permission Denied**: Verify `SSH_USER` has necessary permissions on target nodes

### Getting Help

- Review validation reports in `REPORT_DIR`
- Check error messages in console output
- Verify network connectivity to target servers
- Ensure database user has read permissions

## Example Workflow

```bash
# 1. Configure servers
# Edit config.py and add your Jira node hostnames

# 2. Set database password
export ATLASSIAN_DB_PASSWORD="your_password"

# 3. Run validation
python3 multi_server_executor_v2.py

# 4. Review reports
# Check reports/ directory for validation results
```

## Files Overview

- `config.py`: Main configuration file
- `jira_node_validator_v10.py`: Single-node validation script
- `multi_server_executor_v2.py`: Multi-server parallel execution
- `app.py`: Web interface (if available)
- `requirements.txt`: Python dependencies

---

**Note**: This is production-ready code. Replace "TOKEN" placeholder with actual database password before execution.

