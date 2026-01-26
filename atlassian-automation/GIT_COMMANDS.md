# Git Commands for Repository Setup

## Clone and Check-In Instructions

Use these commands to clone the repository and check in your automation scripts.

---

## Step 1: Clone the Repository

```bash
# Navigate to your desired directory
cd ~/workspace  # or wherever you want to clone

# Clone the repository
git clone git@github.gwd.broadcom.net:GTO/Devops.git

# Navigate into the repository
cd Devops

# Checkout the branch (or create it if it doesn't exist)
git checkout Atlassian_automation

# If branch doesn't exist, create it:
# git checkout -b Atlassian_automation
```

---

## Step 2: Copy Your Automation Folder

```bash
# Copy the atlassian-automation folder to the repository
cp -r /Users/ramanathanm/Downloads/atlassian-automation .

# Or if you want to move it:
# mv /Users/ramanathanm/Downloads/atlassian-automation .
```

---

## Step 3: Review Changes

```bash
# Check what files will be added
git status

# Review the changes (optional)
git diff
```

---

## Step 4: Stage and Commit

```bash
# Stage all files
git add atlassian-automation/

# Or stage specific files
# git add atlassian-automation/jira_load_test_framework/
# git add atlassian-automation/vrli_framework/

# Commit with a descriptive message
git commit -m "Add Atlassian automation frameworks and scripts

- Added jira_load_test_framework for performance testing
- Added vrli_framework for log extraction and analysis
- Added jira_preflight_validator for deployment validation
- Added jira_validator for configuration validation
- Added atlassian_plugin_report for plugin auditing
- Added fetch_groups for LDAP group management
- Added jira_cf_audit for custom field analysis
- Added jira_logparser for log analysis
- Added vrli_poc for vRLI proof of concept
- Added sar_plotter for system performance visualization
- Added atlassian_uploader for file uploads
- Added psirt_mailhandler for email processing
- Sanitized all tokens and passwords (replaced with TOKEN placeholder)
- Added comprehensive README files for each framework"
```

---

## Step 5: Push to Remote

```bash
# Push to remote branch
git push origin Atlassian_automation

# If branch doesn't exist remotely, set upstream:
# git push -u origin Atlassian_automation
```

---

## Complete Command Sequence

Here's the complete sequence you can copy and run:

```bash
# 1. Clone repository
cd ~/workspace
git clone git@github.gwd.broadcom.net:GTO/Devops.git
cd Devops

# 2. Checkout/create branch
git checkout Atlassian_automation || git checkout -b Atlassian_automation

# 3. Copy automation folder
cp -r /Users/ramanathanm/Downloads/atlassian-automation .

# 4. Review changes
git status

# 5. Stage and commit
git add atlassian-automation/
git commit -m "Add Atlassian automation frameworks and scripts

- Added comprehensive automation frameworks for Jira/Confluence
- Sanitized all tokens and passwords
- Added README documentation for each framework"

# 6. Push to remote
git push origin Atlassian_automation
```

---

## Verification

After pushing, verify your changes:

```bash
# Check remote status
git status

# View commit history
git log --oneline -5

# Verify branch exists remotely
git branch -r | grep Atlassian_automation
```

---

## Important Notes

1. **Tokens Sanitized**: All passwords and tokens have been replaced with "TOKEN" placeholder
2. **README Files**: Each framework folder contains a comprehensive README
3. **Production Code**: All code is production-ready (just replace TOKEN placeholders)
4. **No Sensitive Data**: No actual credentials are committed

---

## If You Encounter Issues

### Branch Already Exists
```bash
# If branch exists, just checkout
git checkout Atlassian_automation
git pull origin Atlassian_automation
```

### Merge Conflicts
```bash
# If there are conflicts, resolve them
git pull origin Atlassian_automation
# Resolve conflicts, then:
git add .
git commit -m "Resolve merge conflicts"
git push origin Atlassian_automation
```

### Permission Issues
```bash
# Verify SSH key is set up
ssh -T git@github.gwd.broadcom.net

# If not working, check SSH setup
# See GitHub_Enterprise_SSH_Setup.md for instructions
```

---

**Ready to execute!** Run the commands above to clone and check in your automation frameworks.

