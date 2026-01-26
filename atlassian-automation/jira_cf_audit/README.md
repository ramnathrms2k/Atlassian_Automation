# Jira Custom Field Audit

## Overview

A framework for auditing Jira custom fields to identify usage, empty fields, and stale candidates. This helps with custom field cleanup, optimization, and maintenance.

## What It Does

- **Custom Field Usage Analysis**: Analyzes which custom fields are used and in which projects
- **Empty Field Detection**: Identifies custom fields with no data
- **Stale Field Identification**: Finds custom fields that haven't been updated recently
- **Project-Level Reporting**: Generates reports showing custom field usage per project
- **Database Queries**: Executes optimized SQL queries against Jira database

## Prerequisites

- Bash shell
- MySQL client access
- Database read-only credentials
- Network access to Jira database server

## Configuration

### Main Script: `run_cf_audit.sh`

Edit `run_cf_audit.sh` to configure database connection:

```bash
DB_USER="atlassian_readonly"
DB_PASS="TOKEN"  # Replace TOKEN with actual password
DB_HOST="db-lvnv-it-115.lvn.broadcom.net"
DB_NAME="jiradb"
INPUT_FILE="customfields.txt"
OUTPUT_FILE="customfield_usage_report.csv"
```

**Configuration Parameters:**
- `DB_USER`: Database username (read-only recommended)
- `DB_PASS`: Database password - **Replace "TOKEN" with actual password**
- `DB_HOST`: Database server hostname
- `DB_NAME`: Jira database name
- `INPUT_FILE`: Input file containing custom field IDs and names
- `OUTPUT_FILE`: Output CSV report file

### Input File Format: `customfields.txt`

Create `customfields.txt` with tab-separated custom field data:

```
12345	Custom Field Name 1
12346	Custom Field Name 2
```

**Format**: `CUSTOM_FIELD_ID<TAB>CUSTOM_FIELD_NAME`

### Server Names and Locations

- **Database Server**: Configured in scripts as `DB_HOST`
- **Database Name**: Configured as `DB_NAME` (typically "jiradb")

### Thresholds

- **Stale Field Threshold**: Configured in `5_get_stale_candidates.sh` - defines how old a field must be to be considered "stale"
- **Empty Field Detection**: Fields with zero usage are identified automatically

## How to Use

### 1. Setup

```bash
# Configure database connection in run_cf_audit.sh
# Replace "TOKEN" with actual database password

# Create customfields.txt with your custom field IDs and names
```

### 2. Run Audit

```bash
# Main audit script
./run_cf_audit.sh

# Find empty fields
./3b_find_empty_fields.sh

# Summarize report
./3a_summarize_report.sh

# Get stale candidates
./5_get_stale_candidates.sh

# Summarize stale fields (PROD)
./5a_summarize_PROD_stale.sh

# Verify empty fields
./4_verify_empty_fields.sh

# Verify empty fields (PROD)
./4_verify_empty_fields_prd.sh

# Run audit with PROD verification
./4_run_audit_PROD-VERIFY.sh
```

### 3. Review Output

Check generated CSV files and reports for custom field usage analysis.

## Credentials/Tokens

### Database Credentials

- **Username**: Configured in scripts as `DB_USER`
- **Password**: Set in scripts as `DB_PASS` - **Replace "TOKEN" with actual password**

### Security Notes

- **Never commit passwords to version control**
- Use read-only database user for auditing
- Replace "TOKEN" placeholder with actual password before execution
- Consider using environment variables for passwords in production

## Audit Workflow

1. **Input Preparation**: Create `customfields.txt` with custom field IDs and names
2. **Usage Analysis**: Run `run_cf_audit.sh` to analyze field usage
3. **Empty Field Detection**: Run `3b_find_empty_fields.sh` to find unused fields
4. **Stale Field Analysis**: Run `5_get_stale_candidates.sh` to find old fields
5. **Verification**: Run verification scripts to confirm findings
6. **Reporting**: Review generated CSV reports

## Troubleshooting

### Common Issues

1. **Database Connection Failed**: Verify `DB_HOST`, `DB_USER`, and `DB_PASS` are correct
2. **Permission Denied**: Ensure database user has SELECT permissions
3. **File Not Found**: Verify `customfields.txt` exists and is in correct format
4. **Query Timeout**: Large databases may require query optimization

### Getting Help

- Review error messages in console output
- Verify database connectivity: `mysql -u$DB_USER -p$DB_PASS -h$DB_HOST $DB_NAME -e "SELECT 1"`
- Check input file format (tab-separated)

## Example Workflow

```bash
# 1. Prepare input file
# Create customfields.txt with your custom field data

# 2. Configure database
# Edit run_cf_audit.sh and replace "TOKEN" with actual password

# 3. Run audit
./run_cf_audit.sh

# 4. Analyze empty fields
./3b_find_empty_fields.sh
./3a_summarize_report.sh

# 5. Find stale fields
./5_get_stale_candidates.sh
./5a_summarize_PROD_stale.sh

# 6. Review reports
# Check generated CSV files
```

## Files Overview

- `run_cf_audit.sh`: Main custom field audit script
- `3a_summarize_report.sh`: Summarize audit report
- `3b_find_empty_fields.sh`: Find empty custom fields
- `4_verify_empty_fields.sh`: Verify empty fields
- `4_verify_empty_fields_prd.sh`: Verify empty fields (PROD)
- `4_run_audit_PROD-VERIFY.sh`: Run audit with PROD verification
- `5_get_stale_candidates.sh`: Find stale custom field candidates
- `5a_summarize_PROD_stale.sh`: Summarize stale fields (PROD)

---

**Note**: This is production-ready code. Replace "TOKEN" placeholder with actual database password before execution.

