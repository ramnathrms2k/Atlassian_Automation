# Jira Configuration Validator

## Overview

A validation framework for Jira binary installations and configuration files. This tool verifies Jira binary versions, downloads correct versions if needed, and validates configuration against expected standards.

## What It Does

- **Binary Validation**: Checks Jira binary version and downloads correct version if needed
- **Configuration Validation**: Validates Jira configuration files against expected settings
- **File Integrity**: Verifies critical Jira files are present and correct
- **Version Comparison**: Compares installed version with expected version
- **Automated Fixes**: Can download and prepare correct Jira binaries

## Prerequisites

- Python 3.7+
- Access to Jira installation directory
- Network access to download Jira binaries (if needed)
- Read access to Jira configuration files

## Configuration

### Configuration File: `validator.conf`

Create or edit `validator.conf` in the same directory:

```conf
JIRA_VERSION=10.3.12
JIRA_INSTALL_DIR=/export/jira
DB_VALIDATION_USER=atlassian_readonly
```

**Configuration Parameters:**
- `JIRA_VERSION`: Expected Jira version (e.g., "10.3.12")
- `JIRA_INSTALL_DIR`: Jira installation directory path
- `DB_VALIDATION_USER`: Database user for validation (if database checks are enabled)

### Environment Variables

You can override configuration using environment variables:

```bash
export JIRA_VERSION="10.3.12"
export JIRA_INSTALL_DIR="/export/jira"
export ATLASSIAN_DB_PASSWORD="TOKEN"  # Replace TOKEN with actual password
```

### Server Names and Locations

- **Installation Directory**: Configured in `validator.conf` or `JIRA_INSTALL_DIR` environment variable
- **Binary Location**: Typically `$JIRA_INSTALL_DIR/atlassian-jira-software-<version>/`

### Thresholds

- **Version Matching**: Exact version match required
- **File Existence**: All critical files must be present
- **Configuration Validation**: Config files must match expected format

## How to Use

### 1. Setup

```bash
# Install dependencies (if any)
# Most functionality uses standard library

# Create validator.conf or set environment variables
```

### 2. Run Validation

```bash
# Binary checker
python3 jira_bin_checker_v4.py

# Configuration validator
python3 jira_config_validator_v11.py
```

### 3. Database Validation (Optional)

If database validation is enabled:

```bash
export ATLASSIAN_DB_PASSWORD="TOKEN"  # Replace TOKEN
python3 jira_config_validator_v11.py
```

## Credentials/Tokens

### Database Credentials (Optional)

- **Password**: Set via `ATLASSIAN_DB_PASSWORD` environment variable
- **Replace "TOKEN"**: Replace "TOKEN" placeholder with actual database password if using database validation

### Security Notes

- **Never commit passwords to version control**
- Use environment variables for sensitive data
- Database validation is optional - only needed if database checks are enabled

## Validation Checks

The framework performs:

1. **Binary Version Check**: Verifies Jira binary version
2. **File Existence**: Checks critical files are present
3. **Configuration Validation**: Validates config files
4. **Database Connectivity** (optional): Tests database connection if password provided

## Troubleshooting

### Common Issues

1. **Version Mismatch**: Update `JIRA_VERSION` in `validator.conf`
2. **File Not Found**: Verify `JIRA_INSTALL_DIR` is correct
3. **Permission Denied**: Ensure read access to Jira directory
4. **Database Connection Failed**: Check password and network if using database validation

### Getting Help

- Review error messages in console output
- Verify configuration file format
- Check file permissions on Jira installation directory

## Example Workflow

```bash
# 1. Configure version and directory
echo "JIRA_VERSION=10.3.12" > validator.conf
echo "JIRA_INSTALL_DIR=/export/jira" >> validator.conf

# 2. Run validation
python3 jira_bin_checker_v4.py
python3 jira_config_validator_v11.py

# 3. Review output
# Check console for validation results
```

## Files Overview

- `jira_bin_checker_v4.py`: Binary version validation
- `jira_config_validator_v11.py`: Configuration file validation
- `validator.conf`: Configuration file (create if needed)

---

**Note**: This is production-ready code. Replace "TOKEN" placeholder if using database validation.

