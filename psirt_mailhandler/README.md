# PSIRT Mail Handler

## Overview

A Groovy script for Jira Service Management (JSM) that handles incoming PSIRT (Product Security Incident Response Team) emails and automatically creates or updates Jira issues. This script processes email notifications and integrates them into Jira workflows.

## What It Does

- **Email Processing**: Processes incoming PSIRT email notifications
- **Issue Creation**: Automatically creates Jira issues from email content
- **Issue Updates**: Updates existing issues based on email content
- **Workflow Integration**: Integrates with Jira Service Management workflows
- **Content Parsing**: Extracts relevant information from email content

## Prerequisites

- Jira Service Management (JSM) instance
- Script Runner or similar Groovy execution environment
- Email handler configuration in JSM
- Appropriate permissions to create/update issues

## Configuration

### Script Configuration

The script is typically configured within Jira Service Management:

1. **Go to**: JSM Administration → Automation → Incoming Mail
2. **Configure**: Email handler with this Groovy script
3. **Set**: Appropriate trigger conditions and rules

### Server Names and Locations

- **Jira Instance**: Configured in JSM email handler settings
- **Email Server**: Configured in JSM incoming mail settings

### Thresholds

- **Email Processing**: Configured via JSM email handler rules
- **Issue Creation Rules**: Defined in script logic

## How to Use

### 1. Setup

1. **Access JSM Administration**
2. **Navigate to**: Automation → Incoming Mail
3. **Create/Edit**: Email handler
4. **Add Script**: Copy `psirt_mail_handler.groovy` content
5. **Configure**: Trigger conditions and rules

### 2. Configuration Steps

1. **Email Handler Setup**:
   - Configure email address for PSIRT notifications
   - Set up email server connection
   - Define trigger conditions

2. **Script Configuration**:
   - Add Groovy script to handler
   - Configure issue creation rules
   - Set up field mappings

3. **Testing**:
   - Send test email
   - Verify issue creation
   - Check field population

### 3. Execution

The script runs automatically when:
- Email matching trigger conditions is received
- JSM processes the incoming email
- Script is executed by email handler

## Credentials/Tokens

### JSM Configuration

- **Email Server**: Configured in JSM incoming mail settings
- **Authentication**: Handled by JSM email server configuration

### Security Notes

- **Script runs with JSM system permissions**
- Ensure script has appropriate permissions
- Review script logic for security implications
- Test thoroughly before production deployment

## Script Logic

The script typically:
1. Receives email content
2. Parses email for PSIRT information
3. Extracts issue details (title, description, priority, etc.)
4. Creates or updates Jira issue
5. Links related issues if needed
6. Sends notifications

## Troubleshooting

### Common Issues

1. **Script Not Executing**: Check email handler configuration and triggers
2. **Issue Not Created**: Verify script permissions and Jira project access
3. **Field Mapping Errors**: Check field names and types match Jira configuration
4. **Email Parsing Errors**: Verify email format matches expected pattern

### Getting Help

- Review JSM email handler logs
- Check script execution logs in JSM
- Verify email format and content
- Test with sample emails

## Example Workflow

```groovy
// 1. Configure email handler in JSM
// Go to: Automation → Incoming Mail → Create Handler

// 2. Set trigger conditions
// Email from: psirt@example.com
// Subject contains: "PSIRT"

// 3. Add script
// Copy psirt_mail_handler.groovy content

// 4. Configure issue creation
// Set project, issue type, field mappings

// 5. Test
// Send test email and verify issue creation
```

## Files Overview

- `psirt_mail_handler.groovy`: Groovy script for JSM email handler

---

**Note**: This is production-ready code. Configure in JSM email handler settings before use.

