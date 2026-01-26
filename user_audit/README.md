# User Audit Framework

## Overview

A user auditing framework for Atlassian Jira and Confluence that identifies active licensed users, their departments from HR database, and last login information. This framework helps identify inactive users, ghost licenses, and users not found in HR database for license optimization and compliance.

## What It Does

- **User Discovery**: Fetches all active licensed users from Jira or Confluence
- **HR Integration**: Cross-references users with HR database to get department information
- **Last Login Analysis**: Retrieves and analyzes last login dates for each user
- **License Optimization**: Identifies potential ghost licenses (users not in HR + inactive)
- **Compliance Reporting**: Generates CSV reports for license audit and compliance
- **Multi-Database Support**: Connects to Jira, Confluence, and HR databases

## Prerequisites

### Software Requirements
- **Python**: 3.7 or higher
- **Python Packages**: 
  - `mysql-connector-python` (install via `pip install mysql-connector-python`)
  - `configparser` (usually included in Python standard library)
- **Operating System**: Linux, macOS, or Windows (with WSL recommended for Windows)

### Connectivity Requirements
- **Database Access**:
  - Network connectivity to HR database server
  - Network connectivity to Jira database server
  - Network connectivity to Confluence database server (if auditing Confluence)
  - Database port access (typically 3306 for MySQL)
  - Test connectivity: `mysql -u<USER> -p -h<DB_HOST> -e "SELECT 1"`
- **Firewall Rules**: Ensure database ports are accessible from your machine

### Folder Structure
The framework expects the following structure:
```
user_audit/
├── config.ini                    # Database configuration file
├── user_dept_audit_v2.py         # Main audit script
└── output/                       # Created automatically for CSV reports
```

**Important**:
- All files must be in the same directory
- Script must have execute permissions: `chmod +x user_dept_audit_v2.py` (if needed)
- `config.ini` must be in the same directory as the script
- Output CSV files will be created in the same directory

### Access & Credentials
- **HR Database Credentials**:
  - Database hostname, database name, username, and password
  - Read-only access recommended
  - Access to `tb_hr_employees_all` table
- **Jira Database Credentials**:
  - Database hostname, database name (typically "jiradb"), username, and password
  - Read-only access recommended
  - Access to `cwd_user`, `cwd_membership`, `cwd_group`, `cwd_user_attributes` tables
- **Confluence Database Credentials**:
  - Database hostname, database name (typically "confluence"), username, and password
  - Read-only access recommended
  - Access to `cwd_user`, `cwd_membership`, `cwd_group`, `user_mapping`, `logininfo` tables

### Pre-Execution Checks
Before running audit, verify:
1. ✅ Python 3.7+ installed: `python3 --version`
2. ✅ MySQL connector installed: `pip list | grep mysql-connector`
3. ✅ HR database connectivity: `mysql -u<HR_USER> -p -h<HR_HOST> <HR_DB> -e "SELECT 1"`
4. ✅ Jira database connectivity: `mysql -u<JIRA_USER> -p -h<JIRA_HOST> <JIRA_DB> -e "SELECT 1"`
5. ✅ Confluence database connectivity (if auditing Confluence): `mysql -u<CONF_USER> -p -h<CONF_HOST> <CONF_DB> -e "SELECT 1"`
6. ✅ Configuration file exists: `test -f config.ini && echo "OK"`
7. ✅ Database credentials configured: Check `config.ini` (replace "TOKEN" placeholders)
8. ✅ Write permissions: Ensure directory is writable for output CSV files
9. ✅ Sufficient disk space for output files

## Configuration

### Main Configuration File: `config.ini`

Edit `config.ini` to configure database connections:

```ini
[HR_DB]
host = ace-lvn-it-03.lvn.broadcom.net
database = hr
user = hr_read
password = TOKEN  # Replace TOKEN with actual password

[JIRA_DB]
host = db-lvnv-it-102.lvn.broadcom.net
database = jiradb
user = atlassian_readonly
password = TOKEN  # Replace TOKEN with actual password

[CONFLUENCE_DB]
host = db-lvnv-it-105.lvn.broadcom.net
database = confluence
user = atlassian_readonly
password = TOKEN  # Replace TOKEN with actual password
```

**Configuration Parameters:**
- `host`: Database server hostname or IP
- `database`: Database name
- `user`: Database username (read-only recommended)
- `password`: Database password - **Replace "TOKEN" with actual password**

### Server Names and Locations

- **HR Database**: Configured in `config.ini` under `[HR_DB]`
- **Jira Database**: Configured in `config.ini` under `[JIRA_DB]`
- **Confluence Database**: Configured in `config.ini` under `[CONFLUENCE_DB]`

### Thresholds

- **Inactivity Threshold**: Hardcoded to 90 days (configurable in script)
  - Users with last login > 90 days ago are considered inactive
  - Modify `threshold_days` variable in script to change threshold
- **Ghost License Detection**: Users not found in HR database AND inactive are flagged as potential ghost licenses

## How to Use

### 1. Setup

```bash
# Install dependencies
pip install mysql-connector-python

# Configure database connections in config.ini
# Replace "TOKEN" placeholders with actual database passwords
```

### 2. Run Audit

```bash
# Audit Jira users
python3 user_dept_audit_v2.py jira

# Audit Confluence users
python3 user_dept_audit_v2.py confluence
```

### 3. Review Output

The script generates a CSV file with timestamp:
- `jira_user_audit_YYYYMMDD_HHMMSS.csv`
- `confluence_user_audit_YYYYMMDD_HHMMSS.csv`

**CSV Columns**:
- User ID
- Email Address
- Display Name
- Department (from HR database, or "NOT FOUND")
- Last Login Date (or "Never" if no login recorded)

### 4. Audit Summary

The script displays a summary:
- Total Licensed Users
- Users NOT in HR DB
- Potential Ghost Licenses (users not in HR + inactive)

## Credentials/Tokens

### Database Credentials

- **HR Database**: Configured in `config.ini` under `[HR_DB]`
  - **Replace "TOKEN"**: Replace "TOKEN" placeholder with actual HR database password
- **Jira Database**: Configured in `config.ini` under `[JIRA_DB]`
  - **Replace "TOKEN"**: Replace "TOKEN" placeholder with actual Jira database password
- **Confluence Database**: Configured in `config.ini` under `[CONFLUENCE_DB]`
  - **Replace "TOKEN"**: Replace "TOKEN" placeholder with actual Confluence database password

### Security Notes

- **Never commit passwords to version control**
- Use read-only database users for auditing
- Replace "TOKEN" placeholders with actual passwords before execution
- Consider using environment variables for passwords in production
- Rotate database passwords periodically

## Audit Logic

### User Identification
1. **Fetches Active Licensed Users**: Queries `cwd_user` and `cwd_membership` tables
2. **Gets Last Login**: Retrieves last login from `cwd_user_attributes` (Jira) or `logininfo` (Confluence)
3. **Cross-References HR**: Looks up user in HR database `tb_hr_employees_all` table
4. **Identifies Inactive Users**: Flags users with last login > 90 days ago
5. **Flags Ghost Licenses**: Identifies users not in HR database AND inactive

### Group Membership
- **Jira**: Queries users in `jira-users` group
- **Confluence**: Queries users in `confluence-users` group

## Troubleshooting

### Common Issues

1. **Database Connection Failed**: 
   - Verify `host`, `user`, `password`, and `database` in `config.ini`
   - Test connectivity: `mysql -u<USER> -p -h<HOST> <DB> -e "SELECT 1"`
   - Check firewall rules for database port access

2. **Permission Denied**: 
   - Ensure database users have SELECT permissions
   - Verify read access to required tables

3. **No Users Found**: 
   - Check group names match (`jira-users` or `confluence-users`)
   - Verify users are active in the system
   - Check database table names match your Jira/Confluence version

4. **HR Database Lookup Fails**: 
   - Verify HR database connectivity
   - Check `tb_hr_employees_all` table exists and is accessible
   - Verify userid format matches between systems

5. **Last Login Not Found**: 
   - For Jira: Check `cwd_user_attributes` table has `login.lastLoginMillis` attribute
   - For Confluence: Check `user_mapping` and `logininfo` tables are accessible
   - Some users may never have logged in (will show "Never")

### Getting Help

- Review error messages in console output
- Verify database connectivity to all three databases
- Check table names match your Jira/Confluence version
- Verify user permissions on database tables
- Test queries manually in database client

## Example Workflow

```bash
# 1. Configure databases
# Edit config.ini and replace "TOKEN" with actual passwords

# 2. Install dependencies
pip install mysql-connector-python

# 3. Test database connectivity
mysql -uhr_read -p -hace-lvn-it-03.lvn.broadcom.net hr -e "SELECT 1"
mysql -uatlassian_readonly -p -hdb-lvnv-it-102.lvn.broadcom.net jiradb -e "SELECT 1"

# 4. Run Jira audit
python3 user_dept_audit_v2.py jira

# 5. Run Confluence audit
python3 user_dept_audit_v2.py confluence

# 6. Review output
# Check generated CSV files: jira_user_audit_*.csv and confluence_user_audit_*.csv
# Review audit summary in console output
```

## Output Format

### CSV File Structure
```csv
User ID,Email Address,Display Name,Department,Last Login Date
user123,user@example.com,John Doe,Engineering,2024-10-15
user456,user2@example.com,Jane Smith,NOT FOUND,Never
```

### Audit Summary Example
```
--------------------------------------------------
AUDIT SUMMARY FOR JIRA
--------------------------------------------------
Total Licensed Users:      1250
Users NOT in HR DB:         45
Potential Ghost Licenses:    12
--------------------------------------------------
[SUCCESS] File saved: jira_user_audit_20250109_143022.csv
```

## Files Overview

- `config.ini`: Database configuration file (contains connection details)
- `user_dept_audit_v2.py`: Main audit script

---

**Note**: This is production-ready code. Replace all "TOKEN" placeholders in `config.ini` with actual database passwords before execution.

