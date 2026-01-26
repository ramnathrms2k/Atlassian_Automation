# LDAP Group Fetcher

## Overview

A set of scripts for fetching and analyzing LDAP groups, particularly focused on Atlassian-related groups (Jira, Confluence, Okta-mastered groups). These scripts help with group auditing, member analysis, and access management.

## What It Does

- **Group Discovery**: Fetches LDAP groups matching specific filters (Atlassian, Okta-mastered groups)
- **Member Analysis**: Analyzes group membership and generates reports
- **Audit Reporting**: Creates audit reports for group access and permissions
- **Bucket Analysis**: Analyzes group distribution and patterns
- **Multi-Format Output**: Supports various output formats for analysis

## Prerequisites

- Bash shell
- LDAP tools (`ldapsearch`)
- LDAP access credentials
- Network access to LDAP server

## Configuration

### Main Configuration File: `ldap_config.cfg`

Edit `ldap_config.cfg` to configure LDAP connection:

```bash
LDAP_HOST="rnd-ldap-lvn.lvn.broadcom.net"
LDAP_PORT="636"
LDAP_BIND_DN="your_username@broadcom.net"
LDAP_BASE_DN="DC=Broadcom,DC=net"
LDAP_FILTER='(&(objectCategory=Group)(|(cn=*Okta_Mastered_Division*)(cn=*OM_Division*)(cn=*Okta_Mastered_Jira*)(cn=*Okta_Mastered_Confluence*)(cn=*OM_Confluence*)(cn=*OM_Jira*)(cn=vcf_awf_*)(cn=OKTA_Mastered_Employees_Only)(cn=OKTA_Mastered_Contractors_Only)(extensionName=*ATL_Apps*)))'
LDAP_ATTRS="cn managedBy description extensionName"
```

**Configuration Parameters:**
- `LDAP_HOST`: LDAP server hostname
- `LDAP_PORT`: LDAP port (636 for LDAPS)
- `LDAP_BIND_DN`: Your LDAP bind DN (usually your email/UPN)
- `LDAP_BASE_DN`: LDAP base distinguished name
- `LDAP_FILTER`: LDAP search filter for groups
- `LDAP_ATTRS`: Attributes to fetch from groups

### Server Names and Locations

- **LDAP Server**: Configured in `ldap_config.cfg` as `LDAP_HOST`
- **LDAP Port**: Configured as `LDAP_PORT` (typically 636 for LDAPS)

### Thresholds

- **Group Filters**: Configured in `LDAP_FILTER` - modify to match your group naming patterns
- **Page Size**: LDAP paging is enabled (1000 records per page) to handle large result sets

## How to Use

### 1. Setup

```bash
# Configure LDAP connection in ldap_config.cfg
# Update LDAP_HOST, LDAP_BIND_DN, and other parameters
```

### 2. Run Scripts

```bash
# Basic group fetch
./fetch_groups.sh

# Fetch groups with member details
./fetch_groups_with_members.sh

# Enhanced version with additional features
./fetch_groups_v2.sh

# Analyze group buckets/distribution
./analyze_buckets.sh

# Generate audit actions report
./generate_audit_actions.sh

# Generate audit report
./generate_audit_report.sh
```

### 3. Authentication

Scripts will prompt for LDAP password interactively, or you can set it via environment variable:

```bash
export LDAP_PASS="your_password"
./fetch_groups.sh
```

## Credentials/Tokens

### LDAP Credentials

- **Bind DN**: Configured in `ldap_config.cfg` as `LDAP_BIND_DN`
- **Password**: Prompted interactively or set via `LDAP_PASS` environment variable

### Security Notes

- **Never commit passwords to version control**
- Use environment variables for passwords
- LDAP password is prompted securely (hidden input)
- Consider using service accounts for automation

## Filter Configuration

The `LDAP_FILTER` in `ldap_config.cfg` controls which groups are fetched. Modify it to match your organization's group naming:

- `*Okta_Mastered_Jira*`: Okta-mastered Jira groups
- `*Okta_Mastered_Confluence*`: Okta-mastered Confluence groups
- `*OM_Jira*`: Organization-managed Jira groups
- `*OM_Confluence*`: Organization-managed Confluence groups
- `vcf_awf_*`: VCF workflow groups
- `extensionName=*ATL_Apps*`: Atlassian app extension groups

## Troubleshooting

### Common Issues

1. **LDAP Connection Failed**: Verify `LDAP_HOST` and `LDAP_PORT` are correct
2. **Authentication Failed**: Check `LDAP_BIND_DN` and password
3. **No Results**: Verify `LDAP_FILTER` matches your group naming patterns
4. **Certificate Errors**: LDAPS may require certificate validation - check `LDAPTLS_REQCERT` setting

### Getting Help

- Review error messages in console output
- Verify LDAP server accessibility
- Test LDAP connection manually: `ldapsearch -H ldaps://$LDAP_HOST:$LDAP_PORT -x`

## Example Workflow

```bash
# 1. Configure LDAP connection
# Edit ldap_config.cfg with your LDAP server details

# 2. Fetch groups
./fetch_groups_v2.sh

# 3. Analyze results
./analyze_buckets.sh

# 4. Generate audit report
./generate_audit_report.sh
```

## Files Overview

- `ldap_config.cfg`: LDAP connection configuration
- `fetch_groups.sh`: Basic group fetching script
- `fetch_groups_v2.sh`: Enhanced group fetching with additional features
- `fetch_groups_with_members.sh`: Fetch groups with member details
- `analyze_buckets.sh`: Analyze group distribution
- `generate_audit_actions.sh`: Generate audit action report
- `generate_audit_report.sh`: Generate comprehensive audit report

---

**Note**: This is production-ready code. Configure `ldap_config.cfg` with your LDAP server details before execution.

